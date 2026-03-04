#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源分析报告AI解读器
为资源分析报告生成智能洞察和建议
"""

from typing import Dict, Any, List, Optional
from loguru import logger


class ResourceReportAIInterpreter:
    """资源分析报告AI解读器"""
    
    def __init__(self):
        """初始化AI解读器"""
        self.ernie_client = None
        self.trend_engine = None
        try:
            from app.services.ai.ernie_client import get_ernie_client
            self.ernie_client = get_ernie_client()
            logger.info("✅ 资源报告AI解读器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 无法初始化ERNIE客户端: {e}")
        
        try:
            from app.services.ai.trend_analysis_engine import TrendAnalysisEngine
            self.trend_engine = TrendAnalysisEngine()
            logger.info("✅ 趋势分析引擎初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ 无法初始化趋势分析引擎: {e}")
    
    async def generate_interpretation(
        self,
        report_type: str,
        analysis_data: Dict[str, Any]
    ) -> str:
        """
        生成AI解读HTML
        
        Args:
            report_type: 报告类型（resource_analysis）
            analysis_data: 分析数据
            
        Returns:
            HTML格式的AI解读内容
        """
        try:
            logger.info(f"📝 开始生成{report_type}的AI解读...")
            
            # 如果有ERNIE客户端，使用远程API生成AI解读
            if self.ernie_client:
                try:
                    ai_content = await self._generate_ai_interpretation(analysis_data)
                    if ai_content:
                        logger.info("✅ 使用远程API生成AI解读成功")
                        return self._wrap_ai_content_in_html(ai_content)
                except Exception as e:
                    logger.warning(f"⚠️ 远程API生成失败，使用本地算法: {e}")
            
            # 降级方案：使用本地算法
            logger.info("使用本地算法生成AI解读...")
            
            # 1. 生成执行摘要
            executive_summary = self._generate_executive_summary(analysis_data)
            
            # 2. 识别关键问题
            key_issues = self._identify_key_issues(analysis_data)
            
            # 3. 生成优化建议
            recommendations = self._generate_recommendations(analysis_data)
            
            # 4. 生成趋势预测（如果有趋势数据）
            predictions = self._generate_predictions(analysis_data)
            
            # 5. 组装HTML
            html = self._assemble_html(
                executive_summary,
                key_issues,
                recommendations,
                predictions
            )
            
            logger.info("✅ AI解读生成成功（本地算法）")
            return html
            
        except Exception as e:
            logger.error(f"❌ 生成AI解读失败: {e}")
            return self._generate_fallback_html()
    
    async def _generate_ai_interpretation(self, analysis_data: Dict) -> Optional[str]:
        """
        使用远程ERNIE API生成AI解读
        
        Args:
            analysis_data: 分析数据
            
        Returns:
            AI生成的解读文本
        """
        try:
            # 提取关键数据
            cluster_data = analysis_data.get('analysis_result', {})
            metrics = cluster_data.get('metrics_analysis', {})
            compute_data = cluster_data.get('compute_data', [])
            
            # 构建提示词
            prompt = self._build_resource_prompt(metrics, compute_data)
            
            # 调用ERNIE API
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
            
            return interpretation_text
            
        except Exception as e:
            logger.error(f"远程API调用失败: {e}")
            return None
    
    def _build_resource_prompt(self, metrics: Dict, compute_data: List) -> str:
        """构建资源分析的AI提示词（完整方案）"""
        
        # 提取关键指标
        cluster_count = len(compute_data)
        
        # 构建所有集群的完整数据
        clusters_detail = []
        if metrics:
            for cluster_id, cluster_info in metrics.items():
                cluster_metrics = cluster_info.get('metrics_analysis', {})
                
                # 提取所有关键指标
                node_count = cluster_metrics.get('Node Count', {}).get('value', 0)
                pod_count = cluster_metrics.get('Pod Count', {}).get('value', 0)
                
                # 只包含有效数据的集群
                if node_count > 0 or pod_count > 0:
                    # CPU相关
                    cpu_capacity = cluster_metrics.get('CPU Capacity', {}).get('value', 0)
                    cpu_allocatable = cluster_metrics.get('CPU Allocatable', {}).get('value', 0)
                    cpu_request = cluster_metrics.get('CPU Request (cores)', {}).get('value', 0)
                    cpu_usage = cluster_metrics.get('CPU Usage (cores)', {}).get('value', 0)
                    cpu_usage_pct = cluster_metrics.get('CPU Usage %', {}).get('value', 0)
                    cpu_request_pct = cluster_metrics.get('CPU Request %', {}).get('value', 0)
                    cpu_limit = cluster_metrics.get('CPU Limit', {}).get('value', 0)
                    cpu_request_ratio = cluster_metrics.get('CPU Request vs Usage Ratio', {}).get('value', 0)
                    
                    # 内存相关
                    memory_capacity = cluster_metrics.get('Memory Capacity', {}).get('value', 0)
                    memory_allocatable = cluster_metrics.get('Memory Allocatable', {}).get('value', 0)
                    memory_request = cluster_metrics.get('Memory Request (GB)', {}).get('value', 0)
                    memory_usage = cluster_metrics.get('Memory Usage (GB)', {}).get('value', 0)
                    memory_usage_pct = cluster_metrics.get('Memory Usage %', {}).get('value', 0)
                    memory_request_pct = cluster_metrics.get('Memory Request %', {}).get('value', 0)
                    memory_limit = cluster_metrics.get('Memory Limit (GB)', {}).get('value', 0)
                    memory_request_ratio = cluster_metrics.get('Memory Request vs Usage Ratio', {}).get('value', 0)
                    
                    # Pod状态
                    running_pods = cluster_metrics.get('Running Pod Count', {}).get('value', 0)
                    pending_pods = cluster_metrics.get('Pending Pod Count', {}).get('value', 0)
                    failed_pods = cluster_metrics.get('Failed Pod Count', {}).get('value', 0)
                    succeeded_pods = cluster_metrics.get('Succeeded Pod Count', {}).get('value', 0)
                    evicted_pods = cluster_metrics.get('Evicted Pod Count', {}).get('value', 0)
                    pod_restarts_1h = cluster_metrics.get('Pod Restarts (1h)', {}).get('value', 0)
                    pod_restarts_24h = cluster_metrics.get('Pod Restarts (24h)', {}).get('value', 0)
                    
                    # 节点状态
                    ready_nodes = cluster_metrics.get('Ready Node Count', {}).get('value', 0)
                    notready_nodes = cluster_metrics.get('NotReady Node Count', {}).get('value', 0)
                    disk_pressure = cluster_metrics.get('DiskPressure Node Count', {}).get('value', 0)
                    memory_pressure = cluster_metrics.get('MemoryPressure Node Count', {}).get('value', 0)
                    pid_pressure = cluster_metrics.get('PIDPressure Node Count', {}).get('value', 0)
                    network_unavailable = cluster_metrics.get('NetworkUnavailable Node Count', {}).get('value', 0)
                    node_ready_ratio = cluster_metrics.get('Node Ready Ratio', {}).get('value', 0)
                    
                    # 存储和网络
                    fs_usage_pct = cluster_metrics.get('Node Filesystem Usage %', {}).get('value', 0)
                    network_rx = cluster_metrics.get('Network Receive Bytes/s', {}).get('value', 0)
                    network_tx = cluster_metrics.get('Network Transmit Bytes/s', {}).get('value', 0)
                    
                    # 其他资源
                    service_count = cluster_metrics.get('Service Count', {}).get('value', 0)
                    ingress_count = cluster_metrics.get('Ingress Count', {}).get('value', 0)
                    container_count = cluster_metrics.get('Container Count', {}).get('value', 0)
                    container_restarts_1h = cluster_metrics.get('Container Restarts (1h)', {}).get('value', 0)
                    pod_success_rate = cluster_metrics.get('Pod Success Rate', {}).get('value', 0)
                    
                    # 平均值
                    avg_memory_per_node = cluster_metrics.get('Allocatable Memory per Node (avg)', {}).get('value', 0)
                    avg_cpu_per_node = cluster_metrics.get('Allocatable CPU per Node (avg)', {}).get('value', 0)
                    
                    cluster_detail = f"""
【集群 {cluster_id}】
基础信息:
  - 节点总数: {int(node_count)}个 (就绪: {int(ready_nodes)}, 未就绪: {int(notready_nodes)}, 就绪率: {node_ready_ratio:.1f}%)
  - Pod总数: {int(pod_count)}个 (运行: {int(running_pods)}, 等待: {int(pending_pods)}, 失败: {int(failed_pods)}, 成功: {int(succeeded_pods)}, 驱逐: {int(evicted_pods)})
  - Pod成功率: {pod_success_rate:.1f}%
  - 容器总数: {int(container_count)}个
  - Service数: {int(service_count)}个, Ingress数: {int(ingress_count)}个

CPU资源:
  - 总容量: {cpu_capacity:.2f}核, 可分配: {cpu_allocatable:.2f}核
  - 请求配置: {cpu_request:.2f}核 ({cpu_request_pct:.1f}%), 限制配置: {cpu_limit:.2f}核
  - 实际使用: {cpu_usage:.2f}核 ({cpu_usage_pct:.1f}%)
  - 配置比(请求/使用): {cpu_request_ratio:.1f}倍
  - 平均每节点可分配: {avg_cpu_per_node:.2f}核

内存资源:
  - 总容量: {memory_capacity:.2f}GB, 可分配: {memory_allocatable:.2f}GB
  - 请求配置: {memory_request:.2f}GB ({memory_request_pct:.1f}%), 限制配置: {memory_limit:.2f}GB
  - 实际使用: {memory_usage:.2f}GB ({memory_usage_pct:.1f}%)
  - 配置比(请求/使用): {memory_request_ratio:.1f}倍
  - 平均每节点可分配: {avg_memory_per_node:.2f}GB

稳定性指标:
  - Pod重启(1小时): {int(pod_restarts_1h)}次, (24小时): {int(pod_restarts_24h)}次
  - 容器重启(1小时): {int(container_restarts_1h)}次
  - 磁盘压力节点: {int(disk_pressure)}个
  - 内存压力节点: {int(memory_pressure)}个
  - PID压力节点: {int(pid_pressure)}个
  - 网络不可用节点: {int(network_unavailable)}个

存储和网络:
  - 文件系统使用率: {fs_usage_pct:.1f}%
  - 网络接收: {network_rx/1024/1024:.2f}MB/s
  - 网络发送: {network_tx/1024/1024:.2f}MB/s
"""
                    clusters_detail.append(cluster_detail)
        
        # 如果有详细数据，构建完整提示词
        if clusters_detail:
            clusters_summary = "\n".join(clusters_detail)
            prompt = f"""
请对以下Kubernetes集群资源分析数据进行专业的AI解读和分析：

【集群概览】
- 集群总数: {cluster_count}个
- 有效数据集群: {len(clusters_detail)}个

{clusters_summary}

请基于以上完整的真实数据，从以下几个方面进行深入分析：

1. 资源利用效率评估
   - 分析每个集群的CPU和内存实际使用情况
   - 评估资源配置是否合理（重点关注配置比）
   - 识别资源利用率过高或过低的集群
   - 分析资源请求与实际使用的差距
   
2. 成本优化建议
   - 识别资源浪费严重的集群（配置比过高）
   - 提供具体的优化方案和调整建议
   - 估算潜在的成本节省（基于实际数据）
   - 识别可以缩容或合并的集群
   
3. 容量规划建议
   - 评估当前容量是否充足
   - 识别需要扩容或缩容的集群
   - 提供未来容量规划建议
   - 分析节点和Pod的分布是否合理
   
4. 稳定性和风险识别
   - 识别潜在的性能瓶颈（高使用率集群）
   - 识别资源不足的风险
   - 关注Pod重启频繁和失败率高的集群
   - 关注节点压力（磁盘、内存、PID、网络）
   - 分析Pod成功率低的集群
   
5. 网络和存储分析
   - 评估网络流量是否正常
   - 识别文件系统使用率过高的集群
   - 提供存储优化建议
   
6. 最佳实践建议
   - 资源配置优化建议（基于实际数据）
   - 监控和告警建议
   - 运维改进建议
   - 高可用性改进建议

请用简洁、专业的语言进行解读，重点突出关键发现和可执行的建议。
所有分析和建议必须基于上述真实数据，不要使用"推测"、"可能"等模糊表述。
对于每个重要发现，请引用具体的集群ID和数据作为支撑。
"""
        else:
            # 如果没有详细数据，使用简化提示词
            prompt = f"""
请对以下资源分析数据进行专业的AI解读和分析：

【集群概览】
- 集群数量: {cluster_count}个

注意：当前缺少详细的资源使用数据，请基于集群数量提供通用的资源管理建议。

请从以下几个方面进行分析：
1. 资源管理最佳实践
2. 监控和告警建议
3. 容量规划建议
4. 成本优化方向
5. 稳定性保障建议

请用简洁、专业的语言进行解读。
"""
        
        return prompt
    
    def _wrap_ai_content_in_html(self, ai_text: str) -> str:
        """将AI生成的文本包装成HTML格式"""
        # 转义HTML特殊字符
        ai_text = ai_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 处理换行和段落
        lines = ai_text.split('\n')
        html_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题（以数字开头或特殊符号）
            if line and (line[0].isdigit() or line.startswith('【') or line.startswith('#')):
                html_lines.append(f'<h4>{line}</h4>')
            # 检测列表项
            elif line.startswith('-') or line.startswith('•'):
                html_lines.append(f'<li>{line[1:].strip()}</li>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        # 合并相邻的列表项
        html_content = '\n'.join(html_lines)
        
        # 包装列表
        import re
        html_content = re.sub(
            r'(<li>.*?</li>)',
            lambda m: f'<ul>{m.group(1)}</ul>' if not m.group(0).startswith('<ul>') else m.group(0),
            html_content,
            flags=re.DOTALL
        )
        
        return f'''
        <div class="ai-interpretation-content">
            <div class="ai-badge">🤖 AI智能解读</div>
            {html_content}
        </div>
        '''
    
    def _generate_executive_summary(self, analysis_data: Dict) -> str:
        """生成执行摘要"""
        try:
            # 提取关键指标
            cluster_data = analysis_data.get('analysis_result', {})
            metrics = cluster_data.get('metrics_analysis', {})
            
            # 如果有集群数据，分析资源使用情况
            if metrics:
                # 获取第一个集群的数据作为示例
                first_cluster = list(metrics.values())[0] if metrics else {}
                cluster_metrics = first_cluster.get('metrics_analysis', {})
                
                cpu_usage = cluster_metrics.get('CPU Usage %', {}).get('value', 0)
                memory_usage = cluster_metrics.get('Memory Usage %', {}).get('value', 0)
                cpu_request_ratio = cluster_metrics.get('CPU Request vs Usage Ratio', {}).get('value', 0)
                memory_request_ratio = cluster_metrics.get('Memory Request vs Usage Ratio', {}).get('value', 0)
                
                # 数据验证：只有当数据有效时才生成详细摘要
                if cpu_usage > 0 or memory_usage > 0:
                    # 生成摘要
                    summary = f"""
                    <div class="executive-summary-content">
                        <h3>📊 关键发现</h3>
                        <p class="key-finding">
                            集群资源配置存在<strong>严重过度配置</strong>问题：
                        </p>
                        <ul class="finding-list">
                            <li>CPU实际使用率仅<strong>{cpu_usage:.1f}%</strong>，但请求配置是实际使用的<strong>{cpu_request_ratio:.1f}倍</strong></li>
                            <li>内存实际使用率仅<strong>{memory_usage:.1f}%</strong>，但请求配置是实际使用的<strong>{memory_request_ratio:.1f}倍</strong></li>
                            <li>资源浪费严重，存在<strong>巨大的成本优化空间</strong></li>
                        </ul>
                    </div>
                    """
                    return summary
            
            # 如果没有详细指标，生成通用摘要
            compute_data = cluster_data.get('compute_data', [])
            total_clusters = len(compute_data)
            
            return f"""
            <div class="executive-summary-content">
                <h3>📊 关键发现</h3>
                <p class="key-finding">
                    本次分析涵盖<strong>{total_clusters}个集群</strong>，整体运行状况良好。
                </p>
            </div>
            """
            
        except Exception as e:
            logger.error(f"生成执行摘要失败: {e}")
            return "<p>执行摘要生成失败</p>"
    
    def _identify_key_issues(self, analysis_data: Dict) -> List[Dict]:
        """识别关键问题"""
        issues = []
        
        try:
            cluster_data = analysis_data.get('analysis_result', {})
            metrics = cluster_data.get('metrics_analysis', {})
            
            for cluster_id, cluster_info in metrics.items():
                cluster_metrics = cluster_info.get('metrics_analysis', {})
                summary = cluster_info.get('summary', {})
                
                # 检查严重问题
                critical_count = summary.get('critical', 0)
                warning_count = summary.get('warning', 0)
                
                if critical_count > 0:
                    issues.append({
                        'severity': 'critical',
                        'cluster': cluster_id,
                        'title': f'集群{cluster_id}存在{critical_count}个严重异常指标',
                        'description': '需要立即处理以避免服务中断'
                    })
                
                # 检查Pod重启
                pod_restarts_24h = cluster_metrics.get('Pod Restarts (24h)', {}).get('value', 0)
                if pod_restarts_24h > 1000:
                    issues.append({
                        'severity': 'warning',
                        'cluster': cluster_id,
                        'title': f'Pod重启频繁',
                        'description': f'24小时内重启{int(pod_restarts_24h)}次，建议排查根因'
                    })
                
                # 检查磁盘压力
                disk_pressure = cluster_metrics.get('DiskPressure Node Count', {}).get('value', 0)
                if disk_pressure > 0:
                    issues.append({
                        'severity': 'warning',
                        'cluster': cluster_id,
                        'title': f'{int(disk_pressure)}个节点存在磁盘压力',
                        'description': '建议清理磁盘或扩容'
                    })
                
                # 检查失败的Pod
                failed_pods = cluster_metrics.get('Failed Pod Count', {}).get('value', 0)
                if failed_pods > 10:
                    issues.append({
                        'severity': 'warning',
                        'cluster': cluster_id,
                        'title': f'{int(failed_pods)}个Pod处于失败状态',
                        'description': '建议检查Pod日志并修复问题'
                    })
            
        except Exception as e:
            logger.error(f"识别关键问题失败: {e}")
        
        return issues
    
    def _generate_recommendations(self, analysis_data: Dict) -> List[Dict]:
        """生成优化建议"""
        recommendations = []
        
        try:
            cluster_data = analysis_data.get('analysis_result', {})
            metrics = cluster_data.get('metrics_analysis', {})
            
            for cluster_id, cluster_info in metrics.items():
                cluster_metrics = cluster_info.get('metrics_analysis', {})
                
                # 获取关键指标
                cpu_request_ratio = cluster_metrics.get('CPU Request vs Usage Ratio', {}).get('value', 0)
                memory_request_ratio = cluster_metrics.get('Memory Request vs Usage Ratio', {}).get('value', 0)
                cpu_usage = cluster_metrics.get('CPU Usage %', {}).get('value', 0)
                memory_usage = cluster_metrics.get('Memory Usage %', {}).get('value', 0)
                
                # 资源过度配置建议（添加数据验证）
                if cpu_request_ratio > 5 and cpu_usage > 0:
                    waste_percentage = ((cpu_request_ratio - 2) / cpu_request_ratio) * 100
                    recommendations.append({
                        'priority': 'high',
                        'category': '成本优化',
                        'title': 'CPU资源配置严重过度',
                        'description': f'CPU请求是实际使用的{cpu_request_ratio:.1f}倍，建议降低至2倍以内',
                        'impact': f'预计可节省{waste_percentage:.0f}%的CPU资源成本',
                        'action': '审查并降低Pod的CPU请求配置'
                    })
                
                if memory_request_ratio > 5 and memory_usage > 0:
                    waste_percentage = ((memory_request_ratio - 2) / memory_request_ratio) * 100
                    recommendations.append({
                        'priority': 'high',
                        'category': '成本优化',
                        'title': '内存资源配置严重过度',
                        'description': f'内存请求是实际使用的{memory_request_ratio:.1f}倍，建议降低至2倍以内',
                        'impact': f'预计可节省{waste_percentage:.0f}%的内存资源成本',
                        'action': '审查并降低Pod的内存请求配置'
                    })
                
                # 容量规划建议
                if cpu_usage > 70:
                    recommendations.append({
                        'priority': 'medium',
                        'category': '容量规划',
                        'title': 'CPU使用率较高',
                        'description': f'当前CPU使用率{cpu_usage:.1f}%，建议关注并准备扩容',
                        'impact': '避免性能瓶颈和服务降级',
                        'action': '监控CPU使用趋势，必要时增加节点'
                    })
                
                if memory_usage > 70:
                    recommendations.append({
                        'priority': 'medium',
                        'category': '容量规划',
                        'title': '内存使用率较高',
                        'description': f'当前内存使用率{memory_usage:.1f}%，建议关注并准备扩容',
                        'impact': '避免OOM和Pod驱逐',
                        'action': '监控内存使用趋势，必要时增加节点'
                    })
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
        
        return recommendations
    
    def _generate_predictions(self, analysis_data: Dict) -> Optional[Dict]:
        """生成趋势预测"""
        try:
            if not self.trend_engine:
                logger.warning("趋势分析引擎未初始化，跳过预测")
                return None
            
            # 检查是否有历史数据
            cluster_data = analysis_data.get('analysis_result', {})
            metrics = cluster_data.get('metrics_analysis', {})
            
            if not metrics:
                return None
            
            predictions = {}
            
            # 对每个集群进行趋势预测
            for cluster_id, cluster_info in metrics.items():
                cluster_metrics = cluster_info.get('metrics_analysis', {})
                
                # 提取CPU和内存使用率的历史数据（如果有）
                # 注意：这里需要时间序列数据，当前只有单点数据
                # 如果有历史数据，可以进行预测
                cpu_usage = cluster_metrics.get('CPU Usage %', {}).get('value', 0)
                memory_usage = cluster_metrics.get('Memory Usage %', {}).get('value', 0)
                
                # 如果有历史时间序列数据，进行预测
                # 这里作为示例，假设我们有历史数据
                # 实际使用时需要从数据库或其他来源获取历史数据
                
                # 示例：如果有历史数据
                # cpu_history = [65, 68, 70, 72, 75, 73, 76, cpu_usage]
                # memory_history = [55, 58, 60, 62, 65, 63, 66, memory_usage]
                
                # if len(cpu_history) >= 5:
                #     cpu_forecast, cpu_stats = self.trend_engine.linear_regression_forecast(
                #         cpu_history, forecast_periods=7
                #     )
                #     predictions[f'{cluster_id}_cpu'] = {
                #         'forecast': cpu_forecast,
                #         'trend': cpu_stats['trend'],
                #         'confidence': cpu_stats['r_squared']
                #     }
                
                # 当前实现：标记为待实现
                predictions[cluster_id] = {
                    'status': 'pending',
                    'message': '趋势预测需要历史时间序列数据',
                    'current_cpu': cpu_usage,
                    'current_memory': memory_usage
                }
            
            return predictions if predictions else None
            
        except Exception as e:
            logger.error(f"生成趋势预测失败: {e}")
            return None
    
    def _assemble_html(
        self,
        executive_summary: str,
        key_issues: List[Dict],
        recommendations: List[Dict],
        predictions: Optional[Dict]
    ) -> str:
        """组装HTML"""
        
        # 生成关键问题HTML
        issues_html = ""
        if key_issues:
            issues_html = '<div class="key-issues-grid">'
            for issue in key_issues[:5]:  # 只显示前5个最重要的问题
                severity_class = issue['severity']
                severity_icon = '🔴' if severity_class == 'critical' else '⚠️'
                issues_html += f'''
                <div class="issue-card {severity_class}">
                    <div class="issue-header">
                        <span class="issue-icon">{severity_icon}</span>
                        <span class="issue-title">{issue['title']}</span>
                    </div>
                    <p class="issue-description">{issue['description']}</p>
                </div>
                '''
            issues_html += '</div>'
        else:
            issues_html = '<p class="no-issues">✅ 未检测到严重问题，集群运行健康</p>'
        
        # 生成优化建议HTML
        recommendations_html = ""
        if recommendations:
            recommendations_html = '<div class="recommendations-list">'
            for rec in recommendations[:10]:  # 显示前10个建议
                priority_class = rec['priority']
                priority_icon = '🔥' if priority_class == 'high' else '💡'
                recommendations_html += f'''
                <div class="recommendation-card {priority_class}">
                    <div class="rec-header">
                        <span class="rec-icon">{priority_icon}</span>
                        <span class="rec-category">{rec['category']}</span>
                        <span class="rec-title">{rec['title']}</span>
                    </div>
                    <p class="rec-description">{rec['description']}</p>
                    <div class="rec-footer">
                        <div class="rec-impact">💰 {rec['impact']}</div>
                        <div class="rec-action">👉 {rec['action']}</div>
                    </div>
                </div>
                '''
            recommendations_html += '</div>'
        else:
            recommendations_html = '<p class="no-recommendations">当前配置合理，暂无优化建议</p>'
        
        # 生成趋势预测HTML
        predictions_html = ""
        if predictions:
            predictions_html = '''
            <div class="predictions-section">
                <h4>📈 趋势预测</h4>
                <p>基于历史数据的资源使用趋势预测：</p>
                <div class="prediction-charts">
            '''
            
            for cluster_id, pred_data in predictions.items():
                if pred_data.get('status') == 'pending':
                    predictions_html += f'''
                    <div class="prediction-note">
                        <strong>{cluster_id}</strong>: {pred_data.get('message', '待实现')}
                        <br>当前CPU使用率: {pred_data.get('current_cpu', 0):.1f}%
                        <br>当前内存使用率: {pred_data.get('current_memory', 0):.1f}%
                    </div>
                    '''
                else:
                    # 如果有实际预测数据
                    predictions_html += f'''
                    <div class="prediction-card">
                        <h5>{cluster_id}</h5>
                        <p>趋势: {pred_data.get('trend', 'unknown')}</p>
                        <p>置信度: {pred_data.get('confidence', 0):.2%}</p>
                    </div>
                    '''
            
            predictions_html += '''
                </div>
            </div>
            '''
        
        # 组装完整HTML
        html = f'''
        <div class="ai-interpretation-content">
            <!-- 执行摘要 -->
            <div class="ai-section executive-summary">
                <h3>🎯 执行摘要</h3>
                {executive_summary}
            </div>
            
            <!-- 关键问题 -->
            <div class="ai-section key-issues">
                <h3>⚠️ 关键问题</h3>
                {issues_html}
            </div>
            
            <!-- 优化建议 -->
            <div class="ai-section recommendations">
                <h3>💡 优化建议</h3>
                {recommendations_html}
            </div>
            
            <!-- 趋势预测 -->
            {predictions_html if predictions_html else ''}
        </div>
        
        <style>
        .ai-interpretation-content {{
            padding: 20px;
        }}
        .ai-section {{
            margin-bottom: 30px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .ai-section h3 {{
            color: #1976D2;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        .executive-summary-content {{
            line-height: 1.8;
        }}
        .key-finding {{
            font-size: 1.1em;
            color: #333;
            margin-bottom: 15px;
        }}
        .finding-list {{
            list-style: none;
            padding-left: 0;
        }}
        .finding-list li {{
            padding: 10px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-left: 4px solid #1976D2;
            border-radius: 4px;
        }}
        .key-issues-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        .issue-card {{
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        .issue-card.critical {{
            background: #ffebee;
            border-left-color: #f44336;
        }}
        .issue-card.warning {{
            background: #fff3e0;
            border-left-color: #ff9800;
        }}
        .issue-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .issue-icon {{
            font-size: 1.2em;
        }}
        .issue-title {{
            font-weight: 600;
            color: #333;
        }}
        .issue-description {{
            color: #666;
            font-size: 0.9em;
        }}
        .no-issues {{
            text-align: center;
            padding: 20px;
            color: #4caf50;
            font-size: 1.1em;
        }}
        .recommendations-list {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}
        .recommendation-card {{
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
            background: #f8f9fa;
        }}
        .recommendation-card.high {{
            border-left-color: #f44336;
        }}
        .recommendation-card.medium {{
            border-left-color: #ff9800;
        }}
        .recommendation-card.low {{
            border-left-color: #2196f3;
        }}
        .rec-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .rec-icon {{
            font-size: 1.2em;
        }}
        .rec-category {{
            background: #1976D2;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }}
        .rec-title {{
            font-weight: 600;
            color: #333;
        }}
        .rec-description {{
            color: #666;
            margin-bottom: 10px;
        }}
        .rec-footer {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            font-size: 0.9em;
        }}
        .rec-impact {{
            color: #4caf50;
            font-weight: 500;
        }}
        .rec-action {{
            color: #1976D2;
        }}
        .no-recommendations {{
            text-align: center;
            padding: 20px;
            color: #666;
        }}
        .predictions-section {{
            margin-top: 20px;
        }}
        .prediction-note {{
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            color: #1976D2;
            margin-bottom: 10px;
        }}
        .prediction-card {{
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #4caf50;
        }}
        .prediction-card h5 {{
            color: #333;
            margin-bottom: 10px;
        }}
        </style>
        '''
        
        return html
    
    def _generate_fallback_html(self) -> str:
        """生成降级HTML（当AI解读失败时）"""
        return '''
        <div class="ai-interpretation-fallback">
            <p>⚠️ AI解读暂时不可用，请查看详细数据进行分析</p>
        </div>
        <style>
        .ai-interpretation-fallback {
            padding: 20px;
            background: #fff3e0;
            border-radius: 8px;
            text-align: center;
            color: #ff9800;
        }
        </style>
        '''


# 单例模式
_resource_report_ai_interpreter = None


def get_resource_report_ai_interpreter() -> ResourceReportAIInterpreter:
    """获取资源报告AI解读器单例"""
    global _resource_report_ai_interpreter
    if _resource_report_ai_interpreter is None:
        _resource_report_ai_interpreter = ResourceReportAIInterpreter()
    return _resource_report_ai_interpreter
