#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
报告检索器（Report Retriever）

实现需求：
- Requirements 13.2, 13.3: 时间信息提取和过滤
- Requirements 13.5, 13.6: 向量检索和时间衰减
- Requirements 13.7, 13.8, 13.9: 报告内容获取
- Requirements 16.1, 16.2: 报告缓存
- Requirements 14.1, 14.2, 14.3, 14.4: 报告向量化
"""

import re
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.core.logger import logger
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.vector_store import VectorStore


class ReportRetriever:
    """报告检索器"""
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        vector_store: Optional[VectorStore] = None,
        vector_store_path: str = "/app/vector_store/reports"
    ):
        """
        初始化报告检索器
        
        Args:
            embedding_model: Embedding 模型
            vector_store: 向量存储
            vector_store_path: 向量存储路径
        """
        self.embedding_model = embedding_model or EmbeddingModel()
        self.vector_store = vector_store or VectorStore(
            index_path=vector_store_path
        )
        
        logger.info("✅ 报告检索器初始化成功")
    
    async def retrieve_reports(
        self,
        query: str,
        top_k: int = 5,
        include_details: bool = False
    ) -> List[Dict]:
        """
        检索相关报告
        
        Args:
            query: 用户查询
            top_k: 返回的报告数量
            include_details: 是否包含详细数据
        
        Returns:
            报告列表
        
        Validates:
            - Requirements 13.2, 13.3: 时间信息提取和过滤
            - Requirements 13.5, 13.6: 向量检索和时间衰减
        """
        logger.info(f"🔍 报告检索 - query: {query[:50]}..., top_k: {top_k}")
        
        try:
            # 1. 提取时间信息
            time_filter = self._extract_time_filter(query)
            logger.info(f"📅 时间过滤: {time_filter}")
            
            # 2. 向量化查询
            query_embedding = await self.embedding_model.encode(query)
            
            # 3. 向量检索（应用时间衰减）
            search_results = await self._search_with_time_decay(
                embedding=query_embedding,
                top_k=top_k * 2,  # 多检索一些用于过滤
                time_filter=time_filter
            )
            
            # 4. 获取报告内容
            reports = []
            for result in search_results[:top_k]:
                report_data = await self._get_report_content(
                    task_id=result["metadata"]["task_id"],
                    report_type=result["metadata"]["report_type"],
                    include_details=include_details
                )
                
                if report_data:
                    report_data["similarity"] = result["similarity"]
                    reports.append(report_data)
            
            logger.info(f"✅ 报告检索完成: 返回 {len(reports)} 个报告")
            
            return reports
            
        except Exception as e:
            logger.error(f"❌ 报告检索失败: {e}")
            return []
    
    def _extract_time_filter(self, query: str) -> Dict:
        """
        从查询中提取时间信息
        
        Args:
            query: 用户查询
        
        Returns:
            时间过滤条件
        
        Validates: Requirements 13.2, 13.3
        """
        # 时间模式匹配
        patterns = {
            r"昨天|yesterday": {"days": 1},
            r"上周|last week": {"days": 7},
            r"最近|recent": {"days": 30},
            r"本月|this month": {"days": 30},
            r"上个月|last month": {"days": 60, "offset": 30},
            r"(\d+)天": lambda m: {"days": int(m.group(1))},
            r"(\d+)周": lambda m: {"days": int(m.group(1)) * 7},
        }
        
        for pattern, time_config in patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if callable(time_config):
                    return time_config(match)
                return time_config
        
        # 默认：最近 30 天
        return {"days": 30}
    
    async def _search_with_time_decay(
        self,
        embedding,
        top_k: int,
        time_filter: Dict
    ) -> List[Dict]:
        """
        向量检索（应用时间衰减）
        
        Args:
            embedding: 查询向量
            top_k: 返回数量
            time_filter: 时间过滤条件
        
        Returns:
            检索结果列表
        
        Validates: Requirements 13.5, 13.6
        """
        try:
            # 向量检索
            results = self.vector_store.search(
                embedding,  # 修复：第一个参数是 query_embedding，不是 embedding
                top_k=top_k,
                similarity_threshold=0.3  # 修复：参数名是 similarity_threshold，不是 threshold
            )
            
            # 应用时间过滤和时间衰减
            filtered_results = []
            current_time = datetime.now()
            
            for result in results:
                metadata = result["metadata"]
                
                # 时间过滤
                generated_at = datetime.fromisoformat(metadata.get("generated_at", ""))
                days_ago = (current_time - generated_at).days
                
                if days_ago > time_filter.get("days", 30):
                    continue
                
                # 时间衰减：越新的报告权重越高
                time_decay_factor = 0.1  # 每天衰减 10%
                time_weight = 1.0 - (days_ago * time_decay_factor)
                time_weight = max(0.1, time_weight)  # 最低 0.1
                
                # 调整相似度分数
                adjusted_similarity = result["similarity"] * time_weight
                result["adjusted_similarity"] = adjusted_similarity
                result["time_weight"] = time_weight
                
                filtered_results.append(result)
            
            # 按调整后的相似度排序
            filtered_results.sort(key=lambda x: x["adjusted_similarity"], reverse=True)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"❌ 向量检索失败: {e}")
            return []
    
    async def _get_report_content(
        self,
        task_id: str,
        report_type: str,
        include_details: bool = False
    ) -> Optional[Dict]:
        """
        获取报告内容
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            include_details: 是否包含详细数据
        
        Returns:
            报告内容
        
        Validates: Requirements 13.7, 13.8, 13.9, 16.1, 16.2
        """
        try:
            # TODO: 实际实现中应该：
            # 1. 检查 Redis 缓存
            # 2. 从 MinIO 获取报告文件
            # 3. 提取内容（HTML/JSON）
            # 4. 缓存到 Redis（24 小时）
            
            # 当前返回模拟数据
            report_data = {
                "task_id": task_id,
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "summary": f"这是 {report_type} 类型报告的摘要",
                "conclusion": f"这是 {report_type} 类型报告的结论",
            }
            
            if include_details:
                report_data["details"] = {
                    "data": "详细数据内容"
                }
            
            return report_data
            
        except Exception as e:
            logger.error(f"❌ 获取报告内容失败: {e}")
            return None
    
    def extract_content_layers(
        self,
        content: str,
        report_type: str
    ) -> Dict:
        """
        提取报告内容层级
        
        Args:
            content: 报告内容
            report_type: 报告类型
        
        Returns:
            分层内容
        
        Validates: Requirements 14.1, 14.2, 14.3, 14.4
        """
        if report_type == "resource_analysis":
            return self._extract_resource_analysis_layers(content)
        elif report_type == "bcc_monitoring":
            return self._extract_bcc_monitoring_layers(content)
        elif report_type == "bos_monitoring":
            return self._extract_bos_monitoring_layers(content)
        elif report_type == "operational_analysis":
            return self._extract_operational_analysis_layers(content)
        elif report_type == "eip_monitoring":
            return self._extract_eip_monitoring_layers(content)
        else:
            return {
                "summary": "未知报告类型",
                "conclusion": "",
                "details": content
            }
    
    def _extract_resource_analysis_layers(self, content: str) -> Dict:
        """
        提取资源分析报告内容层级
        
        Validates: Requirements 24.1
        """
        try:
            import re
            
            summary_text = ""
            conclusion_text = ""
            
            # 方法 1：提取 AI 智能解读内容（完整匹配）
            # 使用更精确的正则，匹配整个 ai-interpretation-content 区域
            ai_content_match = re.search(
                r'<div class="ai-interpretation-content">(.*?)</div>\s*</div>\s*</div>',
                content,
                re.DOTALL
            )
            
            if ai_content_match:
                ai_html = ai_content_match.group(1)
                
                # 提取所有段落和列表项
                paragraphs = re.findall(r'<p>(.*?)</p>', ai_html, re.DOTALL)
                list_items = re.findall(r'<li>(.*?)</li>', ai_html, re.DOTALL)
                
                # 清理 HTML 标签和 Markdown 标记
                clean_texts = []
                
                # 处理段落（前20个）
                for p in paragraphs[:20]:
                    clean_p = re.sub(r'<[^>]+>', '', p)
                    clean_p = re.sub(r'\*\*', '', clean_p)  # 移除 Markdown 加粗标记
                    clean_p = re.sub(r'`', '', clean_p)  # 移除代码标记
                    clean_p = re.sub(r'\s+', ' ', clean_p).strip()
                    # 过滤掉 Markdown 标题和过短内容
                    if clean_p and not clean_p.startswith('###') and len(clean_p) > 10:
                        clean_texts.append(clean_p)
                
                # 处理列表项（前15个）
                for li in list_items[:15]:
                    clean_li = re.sub(r'<[^>]+>', '', li)
                    clean_li = re.sub(r'\*\*', '', clean_li)
                    clean_li = re.sub(r'`', '', clean_li)
                    clean_li = re.sub(r'\s+', ' ', clean_li).strip()
                    if clean_li and len(clean_li) > 10:
                        clean_texts.append(f"- {clean_li}")
                
                # 摘要：提取 "资源利用效率评估" 相关的前5条
                summary_parts = []
                for text in clean_texts:
                    if any(keyword in text for keyword in ['CPU和内存', '配置比', '利用率', '实际使用', '集群']):
                        summary_parts.append(text)
                        if len(summary_parts) >= 5:
                            break
                
                summary_text = '\n'.join(summary_parts) if summary_parts else (clean_texts[0] if clean_texts else "")
                
                # 结论：提取 "成本优化" 或包含关键词的内容
                conclusion_parts = []
                for text in clean_texts:
                    if any(keyword in text for keyword in ['成本优化', '容量规划', '稳定性', '风险', '建议', '优化', '浪费', '资源请求']):
                        conclusion_parts.append(text)
                        if len(conclusion_parts) >= 8:
                            break
                
                conclusion_text = '\n'.join(conclusion_parts) if conclusion_parts else '\n'.join(clean_texts[:8])
                
                logger.info(f"✅ 提取到 {len(clean_texts)} 条资源分析内容")
            
            # 方法 2：如果方法 1 失败，提取统计卡片
            if not summary_text:
                logger.warning("⚠️ 方法 1 失败，使用方法 2 提取统计卡片")
                
                stat_cards = re.findall(
                    r'<div class="stat-card">.*?<div class="stat-number">(.*?)</div>.*?<div class="stat-label">(.*?)</div>',
                    content,
                    re.DOTALL
                )
                
                if stat_cards:
                    metrics = []
                    for number, label in stat_cards[:4]:
                        number = re.sub(r'<[^>]+>', '', number).strip()
                        label = re.sub(r'<[^>]+>', '', label).strip()
                        metrics.append(f"{label}: {number}")
                    
                    summary_text = "集群资源分析\n" + "\n".join(metrics)
            
            # 最终 fallback
            if not summary_text:
                summary_text = "资源分析报告"
            
            if not conclusion_text:
                conclusion_text = "集群资源分析完成"
            
            return {
                "summary": summary_text[:500],  # 限制长度
                "conclusion": conclusion_text[:1000],  # 限制长度
                "details": content  # 完整 HTML
            }
            
        except Exception as e:
            logger.error(f"❌ 提取资源分析内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "summary": "资源分析报告",
                "conclusion": "集群资源分析完成",
                "details": content
            }
    
    def _extract_bcc_monitoring_layers(self, content: str) -> Dict:
        """
        提取 BCC 监控报告内容层级
        
        Validates: Requirements 24.2
        """
        try:
            import re
            
            summary_text = ""
            conclusion_text = ""
            
            # 方法 1：提取核心指标统计（作为摘要）
            # 提取异常实例数
            anomaly_count = 0
            anomaly_cards = re.findall(r'<div class="anomaly-card', content)
            if anomaly_cards:
                anomaly_count = len(anomaly_cards)
            
            # 提取使用率分组统计
            group_stats = re.findall(
                r'<h4>([\d\-]+%)</h4>.*?<p class="group-count">(\d+)个实例</p>',
                content,
                re.DOTALL
            )
            
            # 提取优化建议数量
            rec_cards = re.findall(r'<div class="rec-card', content)
            rec_count = len(rec_cards) if rec_cards else 0
            
            # 构建摘要
            summary_parts = []
            summary_parts.append(f"BCC 监控报告")
            if anomaly_count > 0:
                summary_parts.append(f"检测到 {anomaly_count} 个异常实例需要立即关注")
            
            if group_stats:
                summary_parts.append("使用率分组统计:")
                for group_range, count in group_stats:
                    summary_parts.append(f"  {group_range}: {count}个实例")
            
            if rec_count > 0:
                summary_parts.append(f"提供 {rec_count} 项优化建议")
            
            summary_text = "\n".join(summary_parts)
            
            # 方法 2：提取 TOP 10 高使用率实例（作为结论）
            conclusion_parts = []
            
            # 提取 CPU TOP 10
            cpu_section = re.search(
                r'<h3>CPU使用率 TOP 10</h3>.*?<div class="top-list">(.*?)</div>',
                content,
                re.DOTALL
            )
            
            if cpu_section:
                cpu_items = re.findall(
                    r'<span class="instance">(.*?)</span>.*?<span class="value">(.*?)</span>',
                    cpu_section.group(1),
                    re.DOTALL
                )
                
                if cpu_items:
                    conclusion_parts.append("CPU使用率 TOP 5:")
                    for instance, value in cpu_items[:5]:
                        instance = re.sub(r'<[^>]+>', '', instance).strip()
                        value = re.sub(r'<[^>]+>', '', value).strip()
                        conclusion_parts.append(f"  {instance}: {value}")
            
            # 提取内存 TOP 10
            mem_section = re.search(
                r'<h3[^>]*>内存使用率 TOP 10</h3>.*?<div class="top-list">(.*?)</div>',
                content,
                re.DOTALL
            )
            
            if mem_section:
                mem_items = re.findall(
                    r'<span class="instance">(.*?)</span>.*?<span class="value">(.*?)</span>',
                    mem_section.group(1),
                    re.DOTALL
                )
                
                if mem_items:
                    conclusion_parts.append("\n内存使用率 TOP 5:")
                    for instance, value in mem_items[:5]:
                        instance = re.sub(r'<[^>]+>', '', instance).strip()
                        value = re.sub(r'<[^>]+>', '', value).strip()
                        conclusion_parts.append(f"  {instance}: {value}")
            
            # 提取优化建议
            rec_high = re.search(
                r'<div class="rec-card high">.*?<h4>(.*?)</h4>.*?<p>(.*?)</p>',
                content,
                re.DOTALL
            )
            
            rec_medium = re.search(
                r'<div class="rec-card medium">.*?<h4>(.*?)</h4>.*?<p>(.*?)</p>.*?<p class="rec-savings">(.*?)</p>',
                content,
                re.DOTALL
            )
            
            if rec_high or rec_medium:
                conclusion_parts.append("\n优化建议:")
                
                if rec_high:
                    title = re.sub(r'<[^>]+>', '', rec_high.group(1)).strip()
                    desc = re.sub(r'<[^>]+>', '', rec_high.group(2)).strip()
                    conclusion_parts.append(f"  {title}: {desc}")
                
                if rec_medium:
                    title = re.sub(r'<[^>]+>', '', rec_medium.group(1)).strip()
                    desc = re.sub(r'<[^>]+>', '', rec_medium.group(2)).strip()
                    savings = re.sub(r'<[^>]+>', '', rec_medium.group(3)).strip()
                    conclusion_parts.append(f"  {title}: {desc} ({savings})")
            
            conclusion_text = "\n".join(conclusion_parts) if conclusion_parts else "BCC 实例监控分析完成"
            
            # 最终 fallback
            if not summary_text:
                summary_text = "BCC 监控报告"
            
            if not conclusion_text:
                conclusion_text = "BCC 实例监控分析完成"
            
            logger.info(f"✅ 提取到 BCC 监控内容: 异常{anomaly_count}个, 分组{len(group_stats)}个, 建议{rec_count}项")
            
            return {
                "summary": summary_text[:500],
                "conclusion": conclusion_text[:1000],
                "details": content
            }
            
        except Exception as e:
            logger.error(f"❌ 提取 BCC 监控内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "summary": "BCC 监控报告",
                "conclusion": "BCC 实例监控分析完成",
                "details": content
            }
    
    def _extract_bos_monitoring_layers(self, content: str) -> Dict:
        """
        提取 BOS 监控报告内容层级
        
        Validates: Requirements 24.2
        """
        try:
            import re
            
            summary_text = ""
            conclusion_text = ""
            
            # 方法 1：提取 AI 执行摘要（处理 ```html 代码块）
            ai_summary_match = re.search(
                r'<div class="section ai-summary">.*?</div>\s*</div>',
                content,
                re.DOTALL
            )
            
            if ai_summary_match:
                ai_summary_html = ai_summary_match.group(0)
                
                # 移除 ```html 和 ``` 标记
                ai_summary_html = re.sub(r'```html\s*', '', ai_summary_html)
                ai_summary_html = re.sub(r'```\s*', '', ai_summary_html)
                
                # 提取核心发现（作为摘要）
                core_finding = re.search(
                    r'<strong>核心发现：</strong>(.*?)</p>',
                    ai_summary_html,
                    re.DOTALL
                )
                if core_finding:
                    summary_text = "核心发现：" + core_finding.group(1).strip()
                    # 清理 HTML 标签和多余空白
                    summary_text = re.sub(r'<[^>]+>', '', summary_text)
                    summary_text = re.sub(r'\s+', ' ', summary_text).strip()
                
                # 提取关键洞察（补充到摘要）
                key_insights = re.search(
                    r'<strong>关键洞察：</strong>(.*?)</p>',
                    ai_summary_html,
                    re.DOTALL
                )
                if key_insights:
                    insights_text = "关键洞察：" + key_insights.group(1).strip()
                    insights_text = re.sub(r'<[^>]+>', '', insights_text)
                    insights_text = re.sub(r'\s+', ' ', insights_text).strip()
                    if summary_text:
                        summary_text += "\n" + insights_text
                    else:
                        summary_text = insights_text
                
                # 提取主要建议（作为结论）
                main_suggestions = re.search(
                    r'<strong>主要建议：</strong>.*?<ul>(.*?)</ul>',
                    ai_summary_html,
                    re.DOTALL
                )
                if main_suggestions:
                    suggestions_html = main_suggestions.group(1)
                    # 提取所有 <li> 标签内容
                    suggestions = re.findall(r'<li>(.*?)</li>', suggestions_html)
                    if suggestions:
                        conclusion_text = "主要建议：\n" + "\n".join(
                            f"- {re.sub(r'<[^>]+>', '', s).strip()}" 
                            for s in suggestions
                        )
                
                logger.info(f"✅ 提取到 BOS 监控 AI 摘要内容")
            
            # 方法 2：如果方法 1 失败，提取核心指标（作为摘要）
            if not summary_text:
                logger.warning("⚠️ 方法 1 失败，使用方法 2 提取核心指标")
                
                stat_cards = re.findall(
                    r'<div class="stat-card">.*?<div class="stat-number">(.*?)</div>.*?<div class="stat-label">(.*?)</div>',
                    content,
                    re.DOTALL
                )
                
                if stat_cards:
                    metrics = []
                    for number, label in stat_cards[:4]:
                        number = re.sub(r'<[^>]+>', '', number).strip()
                        label = re.sub(r'<[^>]+>', '', label).strip()
                        metrics.append(f"{label}: {number}")
                    
                    summary_text = "BOS 存储核心指标\n" + "\n".join(metrics)
            
            # 方法 3：如果方法 1 失败，提取优化建议（作为结论）
            if not conclusion_text:
                recommendations = re.findall(
                    r'<div class="recommendation-card".*?<h4>(.*?)</h4>.*?<p>(.*?)</p>.*?<p class="action"><strong>建议行动</strong>:\s*(.*?)</p>',
                    content,
                    re.DOTALL
                )
                
                if recommendations:
                    conclusion_parts = []
                    for i, (title, desc, action) in enumerate(recommendations[:3], 1):
                        title = re.sub(r'<[^>]+>', '', title).strip()
                        desc = re.sub(r'<[^>]+>', '', desc).strip()
                        action = re.sub(r'<[^>]+>', '', action).strip()
                        conclusion_parts.append(
                            f"{i}. {title}\n   {desc}\n   建议行动: {action}"
                        )
                    
                    conclusion_text = "优化建议：\n" + "\n\n".join(conclusion_parts)
            
            # 最终 fallback
            if not summary_text:
                summary_text = "BOS 存储分析报告"
            
            if not conclusion_text:
                conclusion_text = "BOS 存储分析完成"
            
            return {
                "summary": summary_text[:500],  # 限制长度
                "conclusion": conclusion_text[:1000],  # 限制长度
                "details": content  # 完整 HTML
            }
            
        except Exception as e:
            logger.error(f"❌ 提取 BOS 监控内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "summary": "BOS 存储分析报告",
                "conclusion": "BOS 存储分析完成",
                "details": content
            }
    
    def _extract_operational_analysis_layers(self, content: str) -> Dict:
        """
        提取运营分析报告内容层级
        
        Validates: Requirements 24.3
        """
        try:
            import re
            
            summary_text = ""
            conclusion_text = ""
            
            # 方法 1：提取核心数据统计（作为摘要）
            # 提取数据概览统计中的核心指标
            overview_cards = re.findall(
                r'<div class="card(?:\s+\w+)?">.*?<div class="card-number">(.*?)</div>.*?<div class="card-label">(.*?)</div>',
                content,
                re.DOTALL
            )
            
            if overview_cards:
                summary_parts = []
                for number, label in overview_cards[:8]:  # 取前8个核心指标
                    number = re.sub(r'<[^>]+>', '', number).strip()
                    label = re.sub(r'<[^>]+>', '', label).strip()
                    summary_parts.append(f"{label}: {number}")
                
                summary_text = "运营数据概览\n" + "\n".join(summary_parts)
            
            # 方法 2：提取 AI 智能解读（作为结论）
            ai_content_match = re.search(
                r'<div class="ai-content">(.*?)</div>\s*</section>',
                content,
                re.DOTALL
            )
            
            if ai_content_match:
                content_html = ai_content_match.group(1)
                # 提取所有段落
                paragraphs = re.findall(r'<p>(.*?)</p>', content_html, re.DOTALL)
                
                if paragraphs:
                    clean_paragraphs = []
                    for p in paragraphs:
                        # 清理 HTML 标签
                        clean_p = re.sub(r'<[^>]+>', '', p)
                        # 清理多余空白
                        clean_p = re.sub(r'\s+', ' ', clean_p).strip()
                        # 过滤掉 Markdown 标题标记和过短的内容
                        if clean_p and not clean_p.startswith('###') and len(clean_p) > 10:
                            clean_paragraphs.append(clean_p)
                    
                    # 结论：取所有 AI 解读段落
                    if clean_paragraphs:
                        conclusion_text = '\n\n'.join(clean_paragraphs)
                    
                    logger.info(f"✅ 提取到 {len(clean_paragraphs)} 段 AI 解读内容")
            
            # 方法 3：如果方法 2 失败，提取硬件故障和人效分析
            if not conclusion_text:
                logger.warning("⚠️ AI 解读提取失败，使用硬件故障和人效分析")
                
                conclusion_parts = []
                
                # 提取硬件故障统计
                hardware_cards = re.findall(
                    r'<h2>硬件故障分析</h2>.*?<div class="card(?:\s+\w+)?">.*?<div class="card-number">(.*?)</div>.*?<div class="card-label">(.*?)</div>',
                    content,
                    re.DOTALL
                )
                
                if hardware_cards:
                    hardware_stats = []
                    for number, label in hardware_cards[:4]:
                        number = re.sub(r'<[^>]+>', '', number).strip()
                        label = re.sub(r'<[^>]+>', '', label).strip()
                        hardware_stats.append(f"{label}: {number}")
                    
                    conclusion_parts.append("硬件故障分析\n" + "\n".join(hardware_stats))
                
                # 提取人效分析（Top 3）
                efficiency_rows = re.findall(
                    r'<h2>人效分析</h2>.*?<tbody>(.*?)</tbody>',
                    content,
                    re.DOTALL
                )
                
                if efficiency_rows:
                    rows = re.findall(r'<tr>(.*?)</tr>', efficiency_rows[0], re.DOTALL)
                    if rows:
                        efficiency_stats = []
                        for row in rows[:3]:  # 取前3个
                            cells = re.findall(r'<td>(.*?)</td>', row)
                            if len(cells) >= 5:
                                name = re.sub(r'<[^>]+>', '', cells[0]).strip()
                                total = re.sub(r'<[^>]+>', '', cells[1]).strip()
                                completed = re.sub(r'<[^>]+>', '', cells[2]).strip()
                                rate = re.sub(r'<[^>]+>', '', cells[4]).strip()
                                efficiency_stats.append(f"{name}: 总数{total}, 完成{completed}, 完成率{rate}")
                        
                        if efficiency_stats:
                            conclusion_parts.append("人效分析（Top 3）\n" + "\n".join(efficiency_stats))
                
                if conclusion_parts:
                    conclusion_text = '\n\n'.join(conclusion_parts)
            
            # 最终 fallback
            if not summary_text:
                summary_text = "运营数据分析报告"
            
            if not conclusion_text:
                conclusion_text = "运营数据分析完成"
            
            return {
                "summary": summary_text[:500],  # 限制长度
                "conclusion": conclusion_text[:1000],  # 限制长度
                "details": content  # 完整 HTML
            }
            
        except Exception as e:
            logger.error(f"❌ 提取运营分析内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "summary": "运营数据分析报告",
                "conclusion": "运营数据分析完成",
                "details": content
            }
    
    def _extract_eip_monitoring_layers(self, content: str) -> Dict:
        """
        提取 EIP 监控报告内容层级
        
        Validates: Requirements 24.4
        """
        try:
            import re
            
            summary_text = ""
            conclusion_text = ""
            
            # 方法 1：提取核心指标（作为摘要）
            stat_cards = re.findall(
                r'<div class="stat-card">.*?<div class="stat-number[^"]*">(.*?)</div>.*?<div class="stat-label">(.*?)</div>',
                content,
                re.DOTALL
            )
            
            if stat_cards:
                summary_parts = ["EIP 流量监控报告"]
                for number, label in stat_cards[:4]:  # 取前4个核心指标
                    number = re.sub(r'<[^>]+>', '', number).strip()
                    label = re.sub(r'<[^>]+>', '', label).strip()
                    summary_parts.append(f"{label}: {number}")
                
                summary_text = "\n".join(summary_parts)
            
            # 方法 2：提取异常检测结果（作为结论的一部分）
            conclusion_parts = []
            
            # 提取异常 EIP 列表
            anomaly_table = re.search(
                r'<h2>异常检测</h2>.*?<tbody>(.*?)</tbody>',
                content,
                re.DOTALL
            )
            
            if anomaly_table:
                anomaly_rows = re.findall(r'<tr>(.*?)</tr>', anomaly_table.group(1), re.DOTALL)
                if anomaly_rows:
                    anomaly_stats = []
                    for row in anomaly_rows[:5]:  # 取前5个异常
                        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                        if len(cells) >= 6:
                            eip_id = re.sub(r'<[^>]+>', '', cells[0]).strip()
                            in_bw = re.sub(r'<[^>]+>', '', cells[1]).strip()
                            out_bw = re.sub(r'<[^>]+>', '', cells[2]).strip()
                            out_drop = re.sub(r'<[^>]+>', '', cells[4]).strip()
                            desc = re.sub(r'<[^>]+>', '', cells[5]).strip()
                            anomaly_stats.append(f"{eip_id}: 入向{in_bw}Mbps, 出向{out_bw}Mbps, {desc}")
                    
                    if anomaly_stats:
                        conclusion_parts.append("异常检测结果（Top 5）:\n" + "\n".join(anomaly_stats))
            
            # 方法 3：提取优化建议
            recommendations = re.findall(
                r'<div class="recommendation-card"[^>]*>.*?<h4>(.*?)</h4>.*?<p>(.*?)</p>.*?<p class="action"><strong>建议行动</strong>:\s*(.*?)</p>',
                content,
                re.DOTALL
            )
            
            if recommendations:
                rec_parts = []
                for i, (title, desc, action) in enumerate(recommendations[:3], 1):  # 取前3个建议
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    desc = re.sub(r'<[^>]+>', '', desc).strip()
                    action = re.sub(r'<[^>]+>', '', action).strip()
                    rec_parts.append(f"{i}. {title}\n   {desc}\n   建议行动: {action}")
                
                if rec_parts:
                    conclusion_parts.append("\n优化建议:\n" + "\n\n".join(rec_parts))
            
            conclusion_text = "\n\n".join(conclusion_parts) if conclusion_parts else "EIP 流量监控分析完成"
            
            # 最终 fallback
            if not summary_text:
                summary_text = "EIP 流量监控报告"
            
            if not conclusion_text:
                conclusion_text = "EIP 流量监控分析完成"
            
            logger.info(f"✅ 提取到 EIP 监控内容: 核心指标{len(stat_cards)}个, 建议{len(recommendations)}项")
            
            return {
                "summary": summary_text[:500],  # 限制长度
                "conclusion": conclusion_text[:1000],  # 限制长度
                "details": content  # 完整 HTML
            }
            
        except Exception as e:
            logger.error(f"❌ 提取 EIP 监控内容失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "summary": "EIP 流量监控报告",
                "conclusion": "EIP 流量监控分析完成",
                "details": content
            }
    
    async def index_report(
        self,
        task_id: str,
        report_type: str,
        file_path: str,
        generated_at: datetime
    ) -> bool:
        """
        索引报告（向量化）
        
        Args:
            task_id: 任务ID
            report_type: 报告类型
            file_path: 文件路径
            generated_at: 生成时间
        
        Returns:
            是否成功
        
        Validates: Requirements 14.1, 14.8, 14.9
        """
        try:
            logger.info(f"📝 索引报告 - task_id: {task_id}, type: {report_type}")
            
            # TODO: 实际实现中应该：
            # 1. 从 MinIO 读取报告文件
            # 2. 提取内容层级（摘要层、结论层）
            # 3. 向量化摘要层和结论层
            # 4. 存储到向量数据库
            # 5. 更新 MySQL report_index 表
            
            # 当前使用模拟数据
            content_text = f"{report_type} 报告摘要和结论"
            embedding = await self.embedding_model.encode(content_text)
            
            # 存储到向量数据库
            vector_id = f"report_{task_id}"
            self.vector_store.add(
                id=vector_id,
                embedding=embedding,
                metadata={
                    "task_id": task_id,
                    "report_type": report_type,
                    "file_path": file_path,
                    "generated_at": generated_at.isoformat(),
                    "indexed_at": datetime.now().isoformat(),
                    "type": "report"
                }
            )
            
            # 保存向量存储
            self.vector_store.save()
            
            logger.info(f"✅ 报告索引完成: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 报告索引失败: {e}")
            return False


# 全局实例（可选）
_report_retriever = None


def get_report_retriever(
    embedding_model: Optional[EmbeddingModel] = None,
    vector_store: Optional[VectorStore] = None
) -> ReportRetriever:
    """获取报告检索器实例"""
    global _report_retriever
    
    if _report_retriever is None:
        _report_retriever = ReportRetriever(embedding_model, vector_store)
    
    return _report_retriever
