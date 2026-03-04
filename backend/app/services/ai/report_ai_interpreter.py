#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
报告 AI 解读服务
在生成 HTML 报告时，调用 ERNIE AI 生成智能解读部分
"""

import json
from typing import Dict, Any, Optional
from loguru import logger

from app.services.ai.ernie_client import ERNIEClient
from app.services.ai.trend_analysis_engine import TrendAnalysisEngine
from app.core.config import settings


class ReportAIInterpreter:
    """报告 AI 解读服务"""
    
    def __init__(self, ernie_client: Optional[ERNIEClient] = None):
        """
        初始化报告 AI 解读服务
        
        Args:
            ernie_client: ERNIE 客户端实例
        """
        self.ernie_client = ernie_client or ERNIEClient()
        self.trend_engine = TrendAnalysisEngine()
        logger.info("✅ 报告 AI 解读服务初始化成功")
    
    async def generate_interpretation(
        self,
        report_type: str,
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        生成报告的 AI 解读
        
        Args:
            report_type: 报告类型（resource_analysis, bcc_monitoring, bos_monitoring, operational_analysis）
            analysis_data: 分析数据
        
        Returns:
            Optional[str]: AI 解读内容（HTML 格式），失败返回 None
        """
        try:
            logger.info(f"📝 开始生成 {report_type} 的 AI 解读...")
            
            # 1. 准备提示词
            prompt = self._prepare_prompt(report_type, analysis_data)
            
            # 2. 调用 AI 生成解读
            interpretation_text = await self.ernie_client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            if not interpretation_text:
                logger.warning(f"⚠️ AI 返回空响应: {report_type}")
                return None
            
            # 3. 转换为 HTML 格式
            html_content = self._format_as_html(interpretation_text)
            
            logger.info(f"✅ AI 解读生成成功: {report_type}")
            return html_content
            
        except Exception as e:
            logger.error(f"❌ 生成 AI 解读失败: {report_type}, 错误: {e}")
            return None
    
    def _prepare_prompt(self, report_type: str, analysis_data: Dict[str, Any]) -> str:
        """
        准备 AI 提示词
        
        Args:
            report_type: 报告类型
            analysis_data: 分析数据
        
        Returns:
            str: 提示词
        """
        # 提取关键数据
        overview = analysis_data.get('overview', {})
        efficiency_data = analysis_data.get('efficiency_data', [])
        hardware_summary = analysis_data.get('hardware_summary', {})
        weekly_trends = analysis_data.get('weekly_trends', [])
        
        # 根据报告类型生成不同的提示词
        if report_type == 'operational_analysis':
            prompt = self._prepare_operational_prompt(overview, efficiency_data, weekly_trends)
        elif report_type == 'resource_analysis':
            prompt = self._prepare_resource_prompt(overview, analysis_data)
        elif report_type in ['bcc_monitoring', 'bos_monitoring']:
            prompt = self._prepare_monitoring_prompt(report_type, overview, analysis_data)
        else:
            prompt = self._prepare_generic_prompt(report_type, analysis_data)
        
        return prompt
    
    def _prepare_operational_prompt(
        self,
        overview: Dict,
        efficiency_data: list,
        weekly_trends: list
    ) -> str:
        """准备运营分析的提示词"""
        
        # 提取关键指标
        total_cards = overview.get('总卡片数', 0)
        avg_weekly = overview.get('平均每周卡片处理量', 0)
        problem_closure_rate = overview.get('问题闭环率', '0%')
        requirement_closure_rate = overview.get('需求闭环率', '0%')
        
        # 人效数据摘要
        efficiency_summary = ""
        if efficiency_data:
            top_performers = sorted(efficiency_data, key=lambda x: x.get('已完成数量', 0), reverse=True)[:3]
            efficiency_summary = "人效排名前三：\n"
            for i, person in enumerate(top_performers, 1):
                efficiency_summary += f"{i}. {person['创建人']}: 完成 {person['已完成数量']} 项，完成率 {person['完成率']}\n"
        
        # 周度趋势摘要和预测
        trend_summary = ""
        forecast_summary = ""
        if weekly_trends:
            latest_week = weekly_trends[-1] if weekly_trends else {}
            trend_summary = f"最近一周：问题跟进 {latest_week.get('问题跟进数', 0)} 项，闭环 {latest_week.get('闭环个数', 0)} 项，解决率 {latest_week.get('问题解决率', '0%')}"
            
            # 使用趋势分析引擎进行预测
            try:
                # 提取历史数据
                follow_counts = [w.get('问题跟进数', 0) for w in weekly_trends]
                close_counts = [w.get('闭环个数', 0) for w in weekly_trends]
                
                if len(follow_counts) >= 3:
                    # 预测下周的问题跟进数
                    follow_forecast, follow_stats = self.trend_engine.linear_regression_forecast(
                        follow_counts, forecast_periods=1
                    )
                    
                    # 预测下周的闭环数
                    close_forecast, close_stats = self.trend_engine.linear_regression_forecast(
                        close_counts, forecast_periods=1
                    )
                    
                    if follow_forecast and close_forecast:
                        predicted_follow = follow_forecast[0]
                        predicted_close = close_forecast[0]
                        predicted_rate = (predicted_close / predicted_follow * 100) if predicted_follow > 0 else 0
                        
                        trend_direction = "上升" if follow_stats.get('trend') == 'increasing' else "下降" if follow_stats.get('trend') == 'decreasing' else "稳定"
                        
                        forecast_summary = f"\n\n【趋势预测】\n"
                        forecast_summary += f"基于历史数据分析，预测下周：\n"
                        forecast_summary += f"- 问题跟进数：约 {predicted_follow:.0f} 项（趋势：{trend_direction}）\n"
                        forecast_summary += f"- 预计闭环数：约 {predicted_close:.0f} 项\n"
                        forecast_summary += f"- 预计解决率：约 {predicted_rate:.1f}%\n"
                        forecast_summary += f"- 预测置信度：{follow_stats.get('r_squared', 0):.2%}\n"
            except Exception as e:
                logger.warning(f"趋势预测失败: {e}")
        
        prompt = f"""
请对以下运营分析数据进行专业的 AI 解读和分析：

【数据概览】
- 总卡片数：{total_cards}
- 平均每周处理量：{avg_weekly}
- 问题闭环率：{problem_closure_rate}
- 需求闭环率：{requirement_closure_rate}

【人效分析】
{efficiency_summary}

【周度趋势】
{trend_summary}
{forecast_summary}

请从以下几个方面进行分析：
1. 整体工作量和处理效率评估
2. 团队人效表现分析（重点关注高效人员的工作方法）
3. 问题和需求的处理进展
4. 基于趋势预测的容量规划建议
5. 存在的主要问题和瓶颈
6. 改进建议和优化方向（具体可执行的建议）

请用简洁、专业的语言进行解读，重点突出关键发现和可执行的建议。
"""
        return prompt
    
    def _prepare_resource_prompt(
        self,
        overview: Dict,
        analysis_data: Dict
    ) -> str:
        """准备资源分析的提示词"""
        
        total_cards = overview.get('总卡片数', 0)
        product_dist = overview.get('product_distribution', [])
        
        product_summary = ""
        if product_dist:
            top_products = product_dist[:5]
            product_summary = "主要产品分布：\n"
            for prod in top_products:
                product_summary += f"- {prod['name']}: {prod['value']} 项 ({prod['percentage']})\n"
        
        prompt = f"""
请对以下资源分析数据进行专业的 AI 解读：

【数据概览】
- 总资源数：{total_cards}

【产品分布】
{product_summary}

请从以下几个方面进行分析：
1. 资源分布特点和规律
2. 主要产品的资源占比分析
3. 资源利用效率评估
4. 潜在的资源瓶颈
5. 资源优化建议

请用简洁、专业的语言进行解读。
"""
        return prompt
    
    def _prepare_monitoring_prompt(
        self,
        report_type: str,
        overview: Dict,
        analysis_data: Dict
    ) -> str:
        """准备监控分析的提示词"""
        
        report_name = "BCC 监控" if report_type == "bcc_monitoring" else "BOS 监控"
        total_items = overview.get('总卡片数', 0)
        
        prompt = f"""
请对以下 {report_name} 数据进行专业的 AI 解读：

【监控概览】
- 监控项总数：{total_items}
- 数据时间：{overview.get('数据时间', '最近')}

请从以下几个方面进行分析：
1. 监控数据的整体健康状况
2. 主要的异常和告警情况
3. 性能指标的趋势分析
4. 潜在的风险和隐患
5. 优化和改进建议

请用简洁、专业的语言进行解读，重点突出关键告警和风险。
"""
        return prompt
    
    def _prepare_generic_prompt(
        self,
        report_type: str,
        analysis_data: Dict
    ) -> str:
        """准备通用提示词"""
        
        data_summary = json.dumps(analysis_data, ensure_ascii=False, indent=2)[:1000]  # 限制长度
        
        prompt = f"""
请对以下 {report_type} 分析数据进行专业的 AI 解读：

【数据摘要】
{data_summary}

请从以下几个方面进行分析：
1. 数据的主要特点和规律
2. 关键指标的评估
3. 存在的问题和瓶颈
4. 改进建议

请用简洁、专业的语言进行解读。
"""
        return prompt
    
    def _format_as_html(self, text: str) -> str:
        """
        将文本格式化为 HTML
        
        Args:
            text: 纯文本内容
        
        Returns:
            str: HTML 格式的内容
        """
        # 转义 HTML 特殊字符
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 处理换行和段落
        lines = text.split('\n')
        html_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题（以数字开头或特殊符号）
            if line and (line[0].isdigit() or line.startswith('【') or line.startswith('【')):
                html_lines.append(f'<h4>{line}</h4>')
            # 检测列表项
            elif line.startswith('-') or line.startswith('•'):
                html_lines.append(f'<li>{line[1:].strip()}</li>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        # 合并相邻的列表项
        html_content = '\n'.join(html_lines)
        html_content = html_content.replace('</li>\n<li>', '</li>\n<li>')
        
        # 包装列表
        import re
        html_content = re.sub(
            r'(<li>.*?</li>)',
            lambda m: f'<ul>{m.group(1)}</ul>' if not m.group(0).startswith('<ul>') else m.group(0),
            html_content,
            flags=re.DOTALL
        )
        
        return html_content


# 全局实例
_interpreter = None


def get_report_ai_interpreter() -> ReportAIInterpreter:
    """获取报告 AI 解读服务实例"""
    global _interpreter
    
    if _interpreter is None:
        _interpreter = ReportAIInterpreter()
    
    return _interpreter
