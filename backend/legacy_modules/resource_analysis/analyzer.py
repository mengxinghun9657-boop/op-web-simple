#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源分析核心模块
从原有modern_gui.py提取并适配为无GUI版本
"""
import json
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class ResourceAnalyzer:
    """资源分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.all_cluster_data = {}
        self.metrics_analysis = {}
    
    def safe_float(self, value, default=0.0):
        """安全转换为浮点数"""
        if value is None or value == "N/A" or value == "":
            return default
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return default

    def safe_int(self, value, default=0):
        """安全转换为整数"""
        if value is None or value == "N/A" or value == "":
            return default
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return default
    
    def analyze_files_integrated(
        self,
        multicluster_file_path: Optional[str] = None,
        excel_file_path: Optional[str] = None,
        cluster_metrics_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        主分析功能 - 整合多数据源
        
        Args:
            multicluster_file_path: Multi-Cluster JSON文件路径
            excel_file_path: Excel文件路径（包含存储/网络/实例工作表）
            cluster_metrics_data: 已获取的集群指标数据（来自Prometheus）
            
        Returns:
            分析结果字典
        """
        try:
            # 分析集群数据
            compute_data = []
            if cluster_metrics_data:
                # 使用传入的Prometheus数据
                self.all_cluster_data = cluster_metrics_data.get('clusters', {})
                compute_data = self.parse_cluster_metrics_data(self.all_cluster_data)
                # 生成基于详细指标的分析
                self.metrics_analysis = self.generate_cluster_metrics_analysis(self.all_cluster_data)
            elif multicluster_file_path:
                compute_data = self.analyze_compute_resources(multicluster_file=multicluster_file_path)
                # 加载data.json中的详细指标数据
                with open(multicluster_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'clusters' in data:
                    self.all_cluster_data = data['clusters']
                    self.metrics_analysis = self.generate_cluster_metrics_analysis(self.all_cluster_data)
            elif excel_file_path:
                # 检查是否有集群工作表
                xl = pd.ExcelFile(excel_file_path)
                if '集群' in xl.sheet_names:
                    compute_df = pd.read_excel(excel_file_path, sheet_name='集群')
                    compute_data = self.analyze_compute_resources(df=compute_df)
                else:
                    print("提示: Excel文件中没有'集群'工作表，将只分析存储/网络/实例数据")
                    compute_data = []
            else:
                raise Exception('必须提供Excel文件、multi-cluster数据文件或cluster_metrics_data')

            # 存储、网络和BCC数据从 Excel 读取
            storage_data = []
            bcc_data = []
            network_data = []
            if excel_file_path:
                try:
                    storage_df = pd.read_excel(excel_file_path, sheet_name='存储')
                    storage_data = self.analyze_storage_resources(storage_df)
                except Exception as e:
                    print(f"警告: 未找到存储工作表 - {e}")

                try:
                    network_df = pd.read_excel(excel_file_path, sheet_name='网络')
                    network_data = self.analyze_network_resources(network_df)
                except Exception as e:
                    print(f"警告: 未找到网络工作表 - {e}")

                # 优先从实例工作表读取BCC数据
                try:
                    instance_df = pd.read_excel(excel_file_path, sheet_name='实例')
                    print(f"成功读取实例工作表，共{len(instance_df)}行数据")
                    bcc_data = self.analyze_bcc_resources(instance_df)
                except Exception as e:
                    print(f"无法读取实例工作表: {e}")
                    bcc_data = []

            # 生成集群分析报告
            cluster_analysis = self.generate_cluster_analysis_report(compute_data)

            return {
                'compute_data': compute_data,
                'storage_data': storage_data,
                'network_data': network_data,
                'bcc_data': bcc_data,
                'cluster_analysis': cluster_analysis,
                'metrics_analysis': self.metrics_analysis,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            raise Exception(f'分析文件时出错: {str(e)}')
    
    def parse_cluster_metrics_data(self, clusters_data: Dict) -> List[Dict]:
        """
        解析Prometheus集群指标数据
        
        Args:
            clusters_data: {cluster_id: {metric_name: value}} 格式
            
        Returns:
            集群列表
        """
        def safe_float(value, default=0.0):
            if value is None or value == 'N/A' or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=0):
            if value is None or value == 'N/A' or value == '':
                return default
            try:
                return int(float(str(value)))
            except (ValueError, TypeError):
                return default
        
        clusters = []
        for cluster_name, cluster_info in clusters_data.items():
            cluster = {
                'name': cluster_name,
                'total_nodes': safe_int(cluster_info.get('Node Count', 0)),
                'total_pods': safe_int(cluster_info.get('Pod Count', 0)),
                'memory_utilization': safe_float(cluster_info.get('Memory Request %', 0)),
                'cpu_utilization': safe_float(cluster_info.get('CPU Request %', 0))
            }
            
            # 根据内存利用率判断健康状态
            memory_util = cluster['memory_utilization']
            if memory_util > 100:
                cluster['health'] = 'critical'
            elif memory_util > 80:
                cluster['health'] = 'warning'
            elif memory_util > 50:
                cluster['health'] = 'attention'
            else:
                cluster['health'] = 'healthy'

            clusters.append(cluster)
        
        return clusters
    
    def analyze_compute_resources(
        self, 
        multicluster_file: Optional[str] = None, 
        df: Optional[pd.DataFrame] = None
    ) -> List[Dict]:
        """分析计算资源 - 支持multi-cluster数据"""
        if multicluster_file:
            return self.parse_multicluster_data(multicluster_file)
        
        # Excel处理逻辑（保留备用）
        return []
    
    def parse_multicluster_data(self, multicluster_file: str) -> List[Dict]:
        """解析multi-cluster输出数据"""
        def safe_int(value, default=0):
            if value is None or value == 'N/A' or value == '':
                return default
            try:
                return int(float(str(value)))
            except (ValueError, TypeError):
                return default
        
        def safe_float(value, default=0.0):
            if value is None or value == 'N/A' or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        clusters = []
        try:
            if multicluster_file.endswith('.json'):
                with open(multicluster_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                clusters_data = data.get('clusters', {})
                
                if isinstance(clusters_data, dict):
                    for cluster_name, cluster_info in clusters_data.items():
                        cluster = {
                            'name': cluster_name,
                            'total_nodes': safe_int(cluster_info.get('Node Count', 0)),
                            'total_pods': safe_int(cluster_info.get('Pod Count', 0)),
                            'memory_utilization': safe_float(cluster_info.get('Memory Request %', 0)),
                            'cpu_utilization': safe_float(cluster_info.get('CPU Request %', 0))
                        }
                        
                        # 健康状态评估
                        memory_util = cluster['memory_utilization']
                        if memory_util > 100:
                            cluster['health'] = 'critical'
                        elif memory_util > 80:
                            cluster['health'] = 'warning'
                        elif memory_util > 50:
                            cluster['health'] = 'attention'
                        else:
                            cluster['health'] = 'healthy'

                        clusters.append(cluster)
        except Exception as e:
            print(f"解析multi-cluster数据时出错: {e}")
            return []
        
        return clusters
    
    def analyze_storage_resources(self, df: pd.DataFrame) -> List[Dict]:
        """存储资源分析"""
        storage_modules = []
        for idx, row in df.iterrows():
            module_name = row['产品模块']
            if pd.isna(module_name) or any(x in str(module_name).upper() for x in ['BCC', 'L20', 'H20', 'H800']):
                continue

            capacity_str = str(row['已创建容量'])
            remaining_str = str(row['剩余可创建容量'])

            capacity_match = re.search(r'([0-9.]+)', capacity_str)
            capacity = float(capacity_match.group(1)) if capacity_match else 0

            remaining_match = re.search(r'([0-9.]+)', remaining_str)
            remaining = float(remaining_match.group(1)) if remaining_match else 0

            total_capacity = capacity + remaining
            utilization = (capacity / total_capacity * 100) if total_capacity > 0 else 0

            if utilization > 90:
                health = 'critical'
            elif utilization > 75:
                health = 'warning'
            elif utilization > 50:
                health = 'attention'
            else:
                health = 'healthy'

            storage_modules.append({
                'name': module_name,
                'total_storage_capacity': total_capacity,
                'total_storage_used': capacity,
                'storage_utilization': utilization,
                'storage_health': health
            })
        
        return storage_modules
    
    def analyze_network_resources(self, df: pd.DataFrame) -> List[Dict]:
        """网络资源分析"""
        network_lines = []
        for idx, row in df.iterrows():
            # 检查专线ID
            dedicate_id = row.get('专线ID')
            if pd.isna(dedicate_id) or dedicate_id == '' or str(dedicate_id).strip() == '':
                continue
            
            # 提取带宽IN数值（支持 "22.3Gb/s" 格式）
            bandwidth_in_str = str(row.get('带宽IN', '0'))
            bandwidth_in_match = re.search(r'([0-9.]+)', bandwidth_in_str)
            bandwidth_in = float(bandwidth_in_match.group(1)) if bandwidth_in_match else 0.0
            
            # 提取带宽OUT数值
            bandwidth_out_str = str(row.get('带宽out', '0'))
            bandwidth_out_match = re.search(r'([0-9.]+)', bandwidth_out_str)
            bandwidth_out = float(bandwidth_out_match.group(1)) if bandwidth_out_match else 0.0
            
            # 提取合计数值
            total_str = str(row.get('合计', '0'))
            total_match = re.search(r'([0-9.]+)', total_str)
            total_bandwidth = float(total_match.group(1)) if total_match else 0.0
            
            # 判断健康状态（基于合计带宽Gb/s）
            health = 'attention' if total_bandwidth > 80 else 'healthy'
            
            network_lines.append({
                'name': str(dedicate_id),
                'bandwidth_in': bandwidth_in,
                'bandwidth_out': bandwidth_out,
                'total_bandwidth': total_bandwidth,
                # 添加带单位的显示字段
                'bandwidth_in_display': f'{bandwidth_in:.2f} Gb/s',
                'bandwidth_out_display': f'{bandwidth_out:.2f} Gb/s',
                'total_display': f'{total_bandwidth:.2f} Gb/s',
                'network_health': health
            })
        
        return network_lines
    
    def analyze_bcc_resources(self, df: pd.DataFrame) -> List[Dict]:
        """分析BCC云服务器资源"""
        bcc_data = []
        if '产品模块' not in df.columns:
            return bcc_data

        for idx, row in df.iterrows():
            module_name = str(row['产品模块']) if pd.notna(row['产品模块']) else ''
            if not any(keyword in module_name.upper() for keyword in ['BCC', 'L20', 'H20', 'H800']):
                continue

            module_upper = module_name.upper()
            if 'L20' in module_upper:
                instance_type = 'L20显卡实例'
                icon = '🎨'
            elif 'H20' in module_upper:
                instance_type = 'H20显卡实例'
                icon = '🚀'
            elif 'H800' in module_upper:
                instance_type = 'H800显卡实例'
                icon = '⚡'
            else:
                # 普通BCC实例使用固定值
                instance_type = '普通BCC实例'
                icon = '☁️'
                bcc_data.append({
                    'name': f'{icon} {instance_type}',
                    'module_name': module_name,
                    'instance_type': instance_type,
                    'server_count': 25580,
                    'cpu_cores': 22605,
                    'memory_tb': 22605,
                    'gpu_count': 0,
                    'gpu_memory': 0,
                    'health': 'healthy'
                })
                continue

            # GPU实例处理
            server_count = row.get('已创建个数', 0)

            cpu_cores = 0
            if 'CPU' in df.columns:
                cpu_match = re.search(r'(\d+)', str(row['CPU']))
                cpu_cores = int(cpu_match.group(1)) if cpu_match else 0

            memory_tb = 0
            for col in ['已创建内存TB']:
                if col in df.columns and pd.notna(row.get(col)):
                    memory_match = re.search(r'([0-9.]+)', str(row[col]))
                    if memory_match:
                        memory_tb = float(memory_match.group(1))
                        break

            gpu_count = 0
            if 'GPU数量' in df.columns and pd.notna(row.get('GPU数量')):
                gpu_count = int(float(row['GPU数量']))

            gpu_memory = 0
            if 'GPU显存GB' in df.columns and pd.notna(row.get('GPU显存GB')):
                gpu_memory = float(row['GPU显存GB'])

            bcc_data.append({
                'name': f'{icon} {instance_type}',
                'module_name': module_name,
                'instance_type': instance_type,
                'server_count': server_count,
                'cpu_cores': cpu_cores,
                'memory_tb': memory_tb,
                'gpu_count': gpu_count,
                'gpu_memory': gpu_memory,
                'health': 'healthy'
            })
        
        return bcc_data
    
    def generate_cluster_analysis_report(self, compute_data: List[Dict]) -> Dict:
        """生成集群分析报告"""
        # 如果有详细指标数据，使用详细分析
        if hasattr(self, 'metrics_analysis') and self.metrics_analysis:
            return self.generate_detailed_metrics_report(compute_data)
        
        # 简单分析
        critical_clusters = [c for c in compute_data if c.get('health') == 'critical']
        warning_clusters = [c for c in compute_data if c.get('health') == 'warning']
        attention_clusters = [c for c in compute_data if c.get('health') == 'attention']
        healthy_clusters = [c for c in compute_data if c.get('health') == 'healthy']

        total_clusters = len(compute_data)
        summary_text = f"本次分析共涉及{total_clusters}个集群，其中健康集群{len(healthy_clusters)}个，需要关注集群{len(attention_clusters)}个，警告集群{len(warning_clusters)}个，严重集群{len(critical_clusters)}个。"

        return {
            'summary': summary_text,
            'critical_clusters': [],
            'warning_clusters': [],
            'attention_clusters': [],
            'recommendations': []
        }
    
    def generate_detailed_metrics_report(self, compute_data: List[Dict]) -> Dict:
        """基于详细指标数据生成分析报告"""
        analysis_report = {
            'summary': '',
            'critical_clusters': [],
            'warning_clusters': [],
            'attention_clusters': [],
            'recommendations': []
        }
        
        total_clusters = len(self.metrics_analysis)
        total_critical = sum(analysis['summary']['critical'] for analysis in self.metrics_analysis.values())
        total_warning = sum(analysis['summary']['warning'] for analysis in self.metrics_analysis.values())
        total_healthy = sum(analysis['summary']['healthy'] for analysis in self.metrics_analysis.values())
        
        # 生成摘要
        summary_text = f"""本次分析共涉及{total_clusters}个集群，基于40+关键指标进行多维度评估：
        严重异常指标：{total_critical}个
        警告级别指标：{total_warning}个  
        正常运行指标：{total_healthy}个"""
        
        analysis_report['summary'] = summary_text

        # 基于详细指标生成集群分析
        for cluster_id, cluster_metrics in self.metrics_analysis.items():
            if 'cluster_id' not in cluster_metrics:
                cluster_metrics['cluster_id'] = cluster_id
            cluster_detail = self._generate_cluster_detail_analysis(cluster_metrics)
            
            if cluster_detail['health'] == 'critical':
                analysis_report['critical_clusters'].append(cluster_detail)
            elif cluster_detail['health'] == 'warning':
                analysis_report['warning_clusters'].append(cluster_detail)
            elif cluster_detail['health'] == 'attention':
                analysis_report['attention_clusters'].append(cluster_detail)

        return analysis_report
    
    def _generate_cluster_detail_analysis(self, cluster_metrics: Dict) -> Dict:
        """基于指标分析生成集群详细分析"""
        cluster_id = cluster_metrics['cluster_id']
        metrics = cluster_metrics.get('metrics_analysis', {})
        summary = cluster_metrics.get('summary', {})
        
        # 提取关键指标
        memory_usage = metrics.get('Memory Usage %', {}).get('value', 0) or 0
        cpu_usage = metrics.get('CPU Usage %', {}).get('value', 0) or 0
        
        # 根据严重指标数量判断健康状态
        critical_count = summary.get('critical', 0)
        warning_count = summary.get('warning', 0)
        
        if critical_count >= 3 or memory_usage > 90 or cpu_usage > 90:
            health = 'critical'
            risk_level = '极高风险'
            analysis_text = f"集群{cluster_id}存在{critical_count}个严重指标异常。内存使用{memory_usage:.1f}%，CPU使用{cpu_usage:.1f}%。需要立即处理。"
            impact_text = "极高风险，可能导致服务中断和数据丢失"
        elif critical_count >= 1 or warning_count >= 5 or memory_usage > 80 or cpu_usage > 75:
            health = 'warning'
            risk_level = '高风险'
            analysis_text = f"集群{cluster_id}存在{critical_count}个严重和{warning_count}个警告指标。内存使用{memory_usage:.1f}%，CPU使用{cpu_usage:.1f}%"
            impact_text = "高风险，可能影响服务性能和稳定性"
        elif warning_count >= 2:
            health = 'attention'
            risk_level = '中等风险'
            analysis_text = f"集群{cluster_id}存在{warning_count}个警告指标。需要持续关注。"
            impact_text = "中等风险，建议制定优化计划"
        else:
            health = 'healthy'
            risk_level = '低风险'
            analysis_text = f"集群{cluster_id}运行健康。所有关键指标均在正常范围内。"
            impact_text = "低风险，运行稳定"
        
        return {
            'name': cluster_id,
            'health': health,
            'memory_utilization': memory_usage,
            'analysis': analysis_text,
            'risk_level': risk_level,
            'impact': impact_text
        }
    
    def generate_cluster_metrics_analysis(self, all_cluster_data: Dict) -> Dict:
        """
        生成集群指标分析
        
        Args:
            all_cluster_data: {cluster_id: {metric_name: value}}
            
        Returns:
            {cluster_id: analysis_result}
        """
        from app.services.prometheus_service import PrometheusService
        
        # 创建服务实例用于分析
        service = PrometheusService()
        
        analysis_results = {}
        for cluster_id, metrics in all_cluster_data.items():
            analysis = self._analyze_single_cluster_metrics(cluster_id, metrics)
            analysis_results[cluster_id] = analysis
        
        return analysis_results
    
    def _analyze_single_cluster_metrics(self, cluster_id: str, metrics: Dict) -> Dict:
        """分析单个集群的指标"""
        def safe_float(value):
            try:
                return float(value) if value not in [None, 'N/A', ''] else 0.0
            except:
                return 0.0
        
        # 指标阈值定义
        thresholds = {
            'Memory Usage %': {'warning': 80, 'critical': 90},
            'CPU Usage %': {'warning': 75, 'critical': 90},
            'Node Filesystem Usage %': {'warning': 80, 'critical': 90},
            'Pod Restarts (1h)': {'warning': 10, 'critical': 20},
            'Failed Pod Count': {'warning': 3, 'critical': 5},
        }
        
        metrics_analysis = {}
        summary = {'critical': 0, 'warning': 0, 'healthy': 0}
        key_issues = []
        
        for metric_name, metric_value in metrics.items():
            value = safe_float(metric_value)
            
            # 判断指标状态
            status = 'healthy'
            if metric_name in thresholds:
                if value >= thresholds[metric_name]['critical']:
                    status = 'critical'
                    summary['critical'] += 1
                    key_issues.append({
                        'metric': metric_name,
                        'value': value,
                        'status': 'critical'
                    })
                elif value >= thresholds[metric_name]['warning']:
                    status = 'warning'
                    summary['warning'] += 1
                    key_issues.append({
                        'metric': metric_name,
                        'value': value,
                        'status': 'warning'
                    })
                else:
                    summary['healthy'] += 1
            
            metrics_analysis[metric_name] = {
                'value': value,
                'status': status
            }
        
        return {
            'cluster_id': cluster_id,
            'metrics_analysis': metrics_analysis,
            'summary': summary,
            'key_issues': key_issues
        }
    def generate_extended_html_report(self, analysis_result, output_path):
        """生成完整交互式HTML报告 - 从资源分析.py复制"""
        import json
        from datetime import datetime

        compute_data = analysis_result.get('compute_data', [])
        storage_data = analysis_result.get('storage_data', [])
        network_data = analysis_result.get('network_data', [])
        bcc_data = analysis_result.get('bcc_data', [])
        cluster_analysis = analysis_result.get('cluster_analysis', {})
        analysis_time = analysis_result.get('analysis_time', '')
        
        # 获取指标分析数据
        metrics_analysis = getattr(self, 'metrics_analysis', {})

        def generate_cluster_analysis_sections():
            sections = ''
            # 严重集群
            if cluster_analysis.get('critical_clusters'):
                sections += '<div class="report-section"><h2 class="section-title">⚠️ 严重集群分析</h2><div class="cluster-analysis-grid">'
                for cluster in cluster_analysis['critical_clusters']:
                    sections += f'''
                    <div class="cluster-analysis-card critical">
                        <div class="cluster-name-analysis">{cluster["name"]}</div>
                        <div class="risk-level critical">{cluster["risk_level"]}</div>
                        <div class="analysis-text">{cluster["analysis"]}</div>
                        <div class="impact-text">影响评估：{cluster["impact"]}</div>
                    </div>'''
                sections += '</div></div>'
            return sections

        total_clusters = len(compute_data)
        total_nodes = sum(c.get('total_nodes', 0) for c in compute_data)
        total_pods = sum(c.get('total_pods', 0) for c in compute_data)
        healthy_count = len([c for c in compute_data if c.get('health') == 'healthy'])
        warning_count = len([c for c in compute_data if c.get('health') == 'warning'])
        attention_count = len([c for c in compute_data if c.get('health') == 'attention'])
        critical_count = len([c for c in compute_data if c.get('health') == 'critical'])

        cluster_names = [c['name'] for c in compute_data]
        memory_utils = [c.get('memory_utilization', 0) for c in compute_data]

        # 计算GPU总数
        total_gpus = 0
        for bcc in bcc_data:
            gpu_count = bcc.get('gpu_count', 0)
            if isinstance(gpu_count, (int, float)):
                total_gpus += int(gpu_count)
            else:
                try:
                    total_gpus += int(str(gpu_count))
                except:
                    pass

        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>长安LCC集群资源分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); min-height: 100vh; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%); color: white; padding: 50px; border-radius: 20px; margin-bottom: 40px; text-align: center; box-shadow: 0 20px 40px rgba(30, 41, 59, 0.3); }}
        .nav-tabs {{ display: flex; background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid rgba(255,255,255,0.2); }}
        .nav-tab {{ flex: 1; padding: 20px; text-align: center; cursor: pointer; border: none; background: transparent; font-size: 15px; font-weight: 600; color: #64748b; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); }}
        .nav-tab.active {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; border-radius: 18px; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(30, 41, 59, 0.3); }}
        .nav-tab:hover {{ background: rgba(30, 41, 59, 0.05); color: #1e293b; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 25px; margin-bottom: 40px; }}
        .stat-card {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; border: 1px solid rgba(255,255,255,0.2); transition: all 0.3s ease; }}
        .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.12); }}
        .stat-number {{ font-size: 2.8em; font-weight: 700; background: linear-gradient(135deg, #1e293b 0%, #475569 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        .stat-label {{ color: #64748b; margin-top: 8px; font-weight: 600; font-size: 0.95em; }}
        .charts-section {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 50px; }}
        .chart-container {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 35px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); height: 420px; border: 1px solid rgba(255,255,255,0.2); }}
        .chart-title {{ font-size: 1.5em; font-weight: 700; color: #1e293b; margin-bottom: 25px; text-align: center; }}
        .chart-wrapper {{ position: relative; height: 320px; }}
        .cluster-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 25px; }}
        .cluster-card {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); border: 1px solid rgba(255,255,255,0.2); }}
        .cluster-card:hover {{ transform: translateY(-8px); box-shadow: 0 25px 50px rgba(0,0,0,0.15); }}
        .cluster-header {{ padding: 25px; color: white; position: relative; }}
        .cluster-card.critical .cluster-header {{ background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%); }}
        .cluster-card.warning .cluster-header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }}
        .cluster-card.attention .cluster-header {{ background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }}
        .cluster-card.healthy .cluster-header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); }}
        .cluster-name {{ font-size: 1.4em; font-weight: 700; margin: 0; }}
        .cluster-body {{ padding: 25px; }}
        .resource-item {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(148, 163, 184, 0.1); }}
        .resource-item:last-child {{ border-bottom: none; }}
        .resource-label {{ color: #64748b; font-weight: 500; }}
        .resource-value {{ color: #1e293b; font-weight: 600; }}
        .filter-section {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 30px; border-radius: 20px; margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid rgba(255,255,255,0.2); }}
        .filter-title {{ font-size: 1.3em; font-weight: 700; color: #1e293b; margin-bottom: 20px; }}
        .filter-buttons {{ display: flex; gap: 15px; flex-wrap: wrap; }}
        .filter-btn {{ padding: 14px 28px; border: 2px solid #64748b; background: rgba(255, 255, 255, 0.8); color: #64748b; border-radius: 30px; cursor: pointer; transition: all 0.3s ease; font-weight: 600; font-size: 0.9em; }}
        .filter-btn:hover, .filter-btn.active {{ background: #64748b; color: white; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(100, 116, 139, 0.3); }}
        .filter-btn.critical {{ border-color: #dc2626; color: #dc2626; }}
        .filter-btn.critical:hover, .filter-btn.critical.active {{ background: #dc2626; color: white; box-shadow: 0 8px 20px rgba(220, 38, 38, 0.3); }}
        .filter-btn.warning {{ border-color: #f59e0b; color: #f59e0b; }}
        .filter-btn.warning:hover, .filter-btn.warning.active {{ background: #f59e0b; color: white; box-shadow: 0 8px 20px rgba(245, 158, 11, 0.3); }}
        .filter-btn.healthy {{ border-color: #10b981; color: #10b981; }}
        .filter-btn.healthy:hover, .filter-btn.healthy.active {{ background: #10b981; color: white; box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3); }}
        .filter-btn.attention {{ border-color: #3b82f6; color: #3b82f6; }}
        .filter-btn.attention:hover, .filter-btn.attention.active {{ background: #3b82f6; color: white; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3); }}
        .analysis-report {{ padding: 20px; }}
        .report-section {{ margin-bottom: 40px; }}
        .section-title {{ font-size: 1.6em; font-weight: 700; color: #1e293b; margin-bottom: 20px; border-bottom: 3px solid #1e293b; padding-bottom: 10px; }}
        .summary-box, .recommendations-box {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 25px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid rgba(255,255,255,0.2); line-height: 1.6; }}
        
        /* 数据表格样式 */
        .data-table-container {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); overflow-x: auto; max-height: 600px; overflow-y: auto; }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; min-width: 1200px; }}
        .data-table th {{ background: linear-gradient(135deg, #1e293b 0%, #334155 100%); color: white; padding: 12px 8px; text-align: center; font-weight: 600; font-size: 0.8em; border: 1px solid #475569; position: sticky; top: 0; z-index: 10; }}
        .data-table td {{ padding: 8px 6px; text-align: center; border: 1px solid #e2e8f0; font-size: 0.85em; }}
        .data-table tbody tr:hover {{ background-color: rgba(59, 130, 246, 0.1); }}
        .data-table tbody tr:nth-child(even) {{ background-color: rgba(248, 250, 252, 0.7); }}
        .cluster-id {{ font-weight: 600; color: #1e293b; min-width: 120px; }}
        .metric-value {{ font-family: 'Consolas', monospace; }}
        .status-critical {{ color: #dc2626; font-weight: 600; }}
        .status-warning {{ color: #f59e0b; font-weight: 600; }}
        .status-healthy {{ color: #10b981; font-weight: 600; }}
        
        .cluster-analysis-grid {{ display: grid; gap: 20px; margin-top: 20px; }}
        .cluster-analysis-card {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border-left: 5px solid; }}
        .cluster-analysis-card.critical {{ border-left-color: #dc2626; }}
        .cluster-analysis-card.warning {{ border-left-color: #f59e0b; }}
        .cluster-analysis-card.attention {{ border-left-color: #3b82f6; }}
        .cluster-name-analysis {{ font-size: 1.2em; font-weight: 600; color: #1e293b; margin-bottom: 10px; }}
        .metrics-summary {{ font-size: 0.9em; color: #64748b; margin-bottom: 8px; font-family: 'Consolas', monospace; background: rgba(248, 250, 252, 0.8); padding: 8px; border-radius: 6px; }}
        .risk-level {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; margin-bottom: 10px; }}
        .risk-level.critical {{ background: #fecaca; color: #dc2626; }}
        .risk-level.warning {{ background: #fed7aa; color: #f59e0b; }}
        .risk-level.attention {{ background: #dbeafe; color: #3b82f6; }}
        .risk-level.healthy {{ background: #dcfce7; color: #16a34a; }}
        .cluster-analysis-card.healthy {{ border-left-color: #16a34a; }}
        .analysis-text {{ color: #64748b; line-height: 1.5; margin-bottom: 10px; }}
        .impact-text {{ color: #1e293b; font-weight: 500; }}
        .recommendation-item {{ margin-bottom: 10px; color: #64748b; line-height: 1.5; }}
        
        /* 指标仪表盘样式 */
        .metrics-dashboard {{ padding: 20px; }}
        .dashboard-header {{ margin-bottom: 30px; text-align: center; }}
        .metric-categories {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 40px; flex-wrap: wrap; }}
        .metric-cat-btn {{ padding: 12px 24px; border: 2px solid #64748b; background: rgba(255, 255, 255, 0.8); color: #64748b; border-radius: 25px; cursor: pointer; transition: all 0.3s ease; font-weight: 600; }}
        .metric-cat-btn:hover, .metric-cat-btn.active {{ background: #64748b; color: white; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(100, 116, 139, 0.3); }}
        .metric-category {{ display: none; }}
        .metric-category.active {{ display: block; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 30px; }}
        .charts-grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 25px; }}
        
        /* 异常告警样式 */
        .anomaly-alerts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 40px; }}
        .alert-section {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 25px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }}
        .alert-section.critical {{ border-left: 5px solid #dc2626; }}
        .alert-section.warning {{ border-left: 5px solid #f59e0b; }}
        .alert-section h3 {{ margin: 0 0 20px 0; font-size: 1.2em; }}
        .alert-list {{ max-height: 300px; overflow-y: auto; }}
        .alert-item {{ background: rgba(248, 250, 252, 0.8); padding: 15px; margin-bottom: 10px; border-radius: 10px; border-left: 3px solid; }}
        .alert-item.critical {{ border-left-color: #dc2626; }}
        .alert-item.warning {{ border-left-color: #f59e0b; }}
        .alert-metric {{ font-weight: 600; color: #1e293b; margin-bottom: 5px; }}
        .alert-message {{ color: #64748b; font-size: 0.9em; }}
        .alert-value {{ float: right; font-weight: 600; }}
        
        /* 指标卡片样式 */
        .metric-card {{ background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px); padding: 20px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); margin-bottom: 20px; }}
        .metric-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .metric-name {{ font-weight: 600; color: #1e293b; }}
        .metric-status {{ padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }}
        .metric-status.healthy {{ background: #dcfce7; color: #16a34a; }}
        .metric-status.warning {{ background: #fed7aa; color: #f59e0b; }}
        .metric-status.critical {{ background: #fecaca; color: #dc2626; }}
        .metric-value {{ font-size: 1.5em; font-weight: 700; margin-bottom: 10px; }}
        .metric-threshold {{ font-size: 0.9em; color: #64748b; }}
        .threshold-bar {{ height: 8px; background: #e2e8f0; border-radius: 4px; margin: 10px 0; overflow: hidden; }}
        .threshold-fill {{ height: 100%; transition: width 0.3s ease; }}
        .threshold-fill.healthy {{ background: linear-gradient(90deg, #10b981, #059669); }}
        .threshold-fill.warning {{ background: linear-gradient(90deg, #f59e0b, #d97706); }}
        .threshold-fill.critical {{ background: linear-gradient(90deg, #dc2626, #b91c1c); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>长安LCC集群资源分析报告</h1>
            <p>生成时间: {analysis_time}</p>
            <p style="margin-top: 15px; font-size: 1.1em;">TAM负责人：<a href="javascript:void(0)" onclick="openRuliu('陈少禄')" style="color: #fbbf24; text-decoration: underline; cursor: pointer;">陈少禄</a></p>
        </div>

        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('overview')">📊 CCE-总览</button>
            <button class="nav-tab" onclick="showTab('metrics')">🎯 指标分析</button>
            <button class="nav-tab" onclick="showTab('compute')">💻 CCE资源详情</button>
            <button class="nav-tab" onclick="showTab('analysis')">📈 集群分析</button>
            <button class="nav-tab" onclick="showTab('storage')">💾 存储资源</button>
            <button class="nav-tab" onclick="showTab('network')">🌐 网络资源</button>
            <button class="nav-tab" onclick="showTab('instances')">☁️ 实例资源</button>
        </div>

        <div id="overview" class="tab-content active">
            <div class="stats">
                <div class="stat-card"><div class="stat-number">{total_clusters}</div><div class="stat-label">K8s集群</div></div>
                <div class="stat-card"><div class="stat-number">{total_nodes}</div><div class="stat-label">节点总数</div></div>
                <div class="stat-card"><div class="stat-number">{total_pods}</div><div class="stat-label">Pod总数</div></div>
                <div class="stat-card"><div class="stat-number">{len(storage_data)}</div><div class="stat-label">存储模块</div></div>
                <div class="stat-card"><div class="stat-number">{len(bcc_data)}</div><div class="stat-label">BCC类型</div></div>
                <div class="stat-card"><div class="stat-number">{total_gpus}</div><div class="stat-label">GPU总数</div></div>
                <div class="stat-card"><div class="stat-number">{critical_count}</div><div class="stat-label">严重集群</div></div>
            </div>

            <div class="charts-section">
                <div class="chart-container">
                    <div class="chart-title">集群健康状态分布</div>
                    <div class="chart-wrapper"><canvas id="healthChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">资源利用率对比</div>
                    <div class="chart-wrapper"><canvas id="overviewChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">节点数量分布</div>
                    <div class="chart-wrapper"><canvas id="nodeChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">Pod密度分析</div>
                    <div class="chart-wrapper"><canvas id="podChart"></canvas></div>
                </div>
            </div>
        </div>

        <div id="metrics" class="tab-content">
            <div class="metrics-dashboard">
                <!-- 指标仪表盘 -->
                <div class="dashboard-header">
                    <h2 class="section-title">🎯 关键指标仪表盘</h2>
                </div>
                
                <!-- 指标类别切换 -->
                <div class="metric-categories">
                    <button class="metric-cat-btn active" onclick="showMetricCategory('resource')">📊 资源利用率</button>
                    <button class="metric-cat-btn" onclick="showMetricCategory('health')">💚 健康状态</button>
                    <button class="metric-cat-btn" onclick="showMetricCategory('performance')">⚡ 性能指标</button>
                    <button class="metric-cat-btn" onclick="showMetricCategory('anomaly')">⚠️ 异常检测</button>
                </div>
                
                <!-- 资源利用率指标 -->
                <div id="resource-metrics" class="metric-category active">
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">内存利用率分布 (实际使用/总容量 %)</div>
                            <div class="chart-wrapper"><canvas id="memoryUtilChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">CPU利用率分布 (实际使用/总容量 %)</div>
                            <div class="chart-wrapper"><canvas id="cpuUtilChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">存储利用率分布 (%)</div>
                            <div class="chart-wrapper"><canvas id="storageUtilChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">资源效率对比 (请求率/使用率/存储率/健康度)</div>
                            <div class="chart-wrapper"><canvas id="efficiencyChart"></canvas></div>
                        </div>
                    </div>
                </div>
                
                <!-- 健康状态指标 -->
                <div id="health-metrics" class="metric-category">
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">节点就绪率 (Ready节点/总节点 %)</div>
                            <div class="chart-wrapper"><canvas id="nodeHealthChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Pod成功率</div>
                            <div class="chart-wrapper"><canvas id="podSuccessChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">节点压力状态</div>
                            <div class="chart-wrapper"><canvas id="nodePressureChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">整体健康趋势</div>
                            <div class="chart-wrapper"><canvas id="healthTrendChart"></canvas></div>
                        </div>
                    </div>
                </div>
                
                <!-- 性能指标 -->
                <div id="performance-metrics" class="metric-category">
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">容器重启统计</div>
                            <div class="chart-wrapper"><canvas id="restartChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">资源请求率对比 (内存/CPU请求vs使用比率 %)</div>
                            <div class="chart-wrapper"><canvas id="requestUsageChart"></canvas></div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">网络流量统计 (MB/s)</div>
                            <div class="chart-wrapper"><canvas id="networkTrafficChart"></canvas></div>
                        </div>
                    </div>
                </div>
                
                <!-- 新增：详细监控指标 -->
                <div id="detailed-metrics" class="metric-category">
                    <h2 class="category-title">📈 详细监控指标</h2>
                    <div class="charts-grid">
                        <div class="chart-card">
                            <div class="chart-title">核心组件统计</div>
                            <div class="chart-wrapper"><canvas id="serviceStatsChart"></canvas></div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">容器状态分布</div>
                            <div class="chart-wrapper"><canvas id="containerStatsChart"></canvas></div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">资源容量对比</div>
                            <div class="chart-wrapper"><canvas id="capacityComparisonChart"></canvas></div>
                        </div>
                        
                        <div class="chart-card">
                            <div class="chart-title">Pod重启趋势</div>
                            <div class="chart-wrapper"><canvas id="restartTrendChart"></canvas></div>
                        </div>
                    </div>
                </div>
                
                <!-- 异常检测 -->
                <div id="anomaly-metrics" class="metric-category">
                    <div class="anomaly-alerts">
                        <div class="alert-section critical">
                            <h3>🚨 严重异常</h3>
                            <div id="critical-alerts" class="alert-list"></div>
                        </div>
                        <div class="alert-section warning">
                            <h3>⚠️ 警告异常</h3>
                            <div id="warning-alerts" class="alert-list"></div>
                        </div>
                    </div>
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">异常指标统计</div>
                            <div class="chart-wrapper"><canvas id="anomalyStatsChart"></canvas></div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Pod状态分布</div>
                            <div class="chart-wrapper"><canvas id="thresholdViolationChart"></canvas></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div id="compute" class="tab-content">
            <div class="filter-section">
                <div class="filter-title">🔍 筛选集群</div>
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterClusters('all')">全部 ({total_clusters})</button>
                    <button class="filter-btn healthy" onclick="filterClusters('healthy')">健康 ({healthy_count})</button>
                    <button class="filter-btn attention" onclick="filterClusters('attention')">注意 ({attention_count})</button>
                    <button class="filter-btn warning" onclick="filterClusters('warning')">警告 ({warning_count})</button>
                    <button class="filter-btn critical" onclick="filterClusters('critical')">严重 ({critical_count})</button>
                </div>
            </div>
            <div class="cluster-grid" id="computeClusters">'''
        # 生成计算资源卡片 - 基于data.json数据
        for cluster in compute_data:
            health = cluster.get('health', 'healthy')
            cluster_name = cluster['name']
            
            # 从data.json获取详细指标
            detailed_metrics = ""
            if hasattr(self, 'all_cluster_data') and cluster_name in self.all_cluster_data:
                cluster_data = self.all_cluster_data[cluster_name]
                memory_usage = self.safe_float(cluster_data.get('Memory Usage %', 0))
                cpu_usage = self.safe_float(cluster_data.get('CPU Usage %', 0))
                pod_restarts = self.safe_int(cluster_data.get('Pod Restarts (1h)', 0))
                failed_pods = self.safe_int(cluster_data.get('Failed Pod Count', 0))
                
                detailed_metrics = f'''
                        <div class="resource-item"><span class="resource-label">实际内存使用</span><span class="resource-value">{memory_usage:.1f}%</span></div>
                        <div class="resource-item"><span class="resource-label">实际CPU使用</span><span class="resource-value">{cpu_usage:.1f}%</span></div>
                        <div class="resource-item"><span class="resource-label">Pod重启(1h)</span><span class="resource-value">{pod_restarts}次</span></div>
                        <div class="resource-item"><span class="resource-label">失败Pod数</span><span class="resource-value">{failed_pods}个</span></div>'''
            
            html_content += f'''
                <div class="cluster-card {health}" data-health="{health}">
                    <div class="cluster-header">
                        <div class="cluster-name">{cluster_name}</div>
                    </div>
                    <div class="cluster-body">
                        <div class="resource-item"><span class="resource-label">节点数量</span><span class="resource-value">{cluster.get('total_nodes', 0)}</span></div>
                        <div class="resource-item"><span class="resource-label">Pod数量</span><span class="resource-value">{cluster.get('total_pods', 0)}</span></div>
                        <div class="resource-item"><span class="resource-label">内存请求率</span><span class="resource-value">{cluster.get('memory_utilization', 0):.1f}%</span></div>{detailed_metrics}
                        <div class="resource-item"><span class="resource-label">健康状态</span><span class="resource-value">{health.upper()}</span></div>
                    </div>
                </div>'''
        html_content += '''
            </div>
        </div>

        <div id="analysis" class="tab-content">
            <div class="analysis-report">
                <div class="report-section">
                    <h2 class="section-title">📈 集群健康状态分析</h2>
                    <div class="summary-box">
                        <p>''' + cluster_analysis.get('summary', '') + '''</p>
                    </div>
                </div>
                
                <!-- 原始数据表格 -->
                <div class="report-section">
                    <h2 class="section-title">📋 集群原始数据总览</h2>
                    <div class="data-table-container">
                        <table class="data-table" id="rawDataTable">
                            <thead>
                                <tr>
                                    <th>集群ID</th>
                                    <th>节点数</th>
                                    <th>Pod数</th>
                                    <th>内存使用率</th>
                                    <th>CPU使用率</th>
                                    <th>存储使用率</th>
                                    <th>内存容量(GB)</th>
                                    <th>内存可分配(GB)</th>
                                    <th>内存请求(GB)</th>
                                    <th>内存使用(GB)</th>
                                    <th>CPU容量(核)</th>
                                    <th>运行Pod</th>
                                    <th>等待Pod</th>
                                    <th>失败Pod</th>
                                    <th>Pod重启(1h)</th>
                                    <th>Pod重启(24h)</th>
                                    <th>容器重启(1h)</th>
                                    <th>网络接收(Bytes/s)</th>
                                    <th>网络发送(Bytes/s)</th>
                                    <th>Service数</th>
                                    <th>Ingress数</th>
                                    <th>容器数</th>
                                    <th>Pod成功率</th>
                                    <th>就绪节点</th>
                                    <th>未就绪节点</th>
                                </tr>
                            </thead>
                            <tbody id="rawDataTableBody">
                                <!-- 数据将通过JavaScript填充 -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="report-section">
                    <h2 class="section-title">📊 所有集群详细分析</h2>
                    <div class="cluster-analysis-grid">'''
        # 显示所有集群的详细分析 - 优先使用指标分析结果
        if hasattr(self, 'metrics_analysis') and self.metrics_analysis:
            # 使用指标分析结果 - 显示多维度分析
            for cluster_id, detailed_analysis in self.metrics_analysis.items():
                # 确保detailed_analysis包含cluster_id信息
                if 'cluster_id' not in detailed_analysis:
                    detailed_analysis['cluster_id'] = cluster_id
                cluster_detail = self._generate_cluster_detail_analysis(detailed_analysis)
                health = cluster_detail['health']
                risk_level = cluster_detail['risk_level']
                analysis_text = cluster_detail['analysis']
                impact_text = cluster_detail['impact']
                
                # 添加关键指标摘要
                metrics_summary = self._generate_metrics_summary(detailed_analysis)
                
                html_content += f'''
                    <div class="cluster-analysis-card {health}">
                        <div class="cluster-name-analysis">{cluster_detail['name']}</div>
                        <div class="risk-level {health}">{risk_level}</div>
                        <div class="metrics-summary">{metrics_summary}</div>
                        <div class="analysis-text">{analysis_text}</div>
                        <div class="impact-text">影响评估：{impact_text}</div>
                    </div>'''
        else:
            # 备用：使用简单的集群数据
            for cluster in compute_data:
                health = cluster.get('health', 'healthy')
                memory_util = cluster.get('memory_utilization', 0)
                nodes = cluster.get('total_nodes', 0)
                pods = cluster.get('total_pods', 0)
                
                if health == 'critical':
                    risk_level = '极高风险'
                    analysis_text = f"集群{cluster['name']}内存利用率达到{memory_util:.1f}%，超出安全阈值。当前运行{pods}个Pod在{nodes}个节点上，平均每节点Pod密度为{pods / nodes if nodes > 0 else 0:.1f}。过高的内存利用率可能导致节点OOM、Pod调度失败等问题。"
                    impact_text = "可能影响业务稳定性，导致服务中断"
                elif health == 'warning':
                    risk_level = '高风险'
                    analysis_text = f"集群{cluster['name']}内存利用率为{memory_util:.1f}%，接近资源上限。当前运行{pods}个Pod在{nodes}个节点上，资源紧张可能影响新Pod的调度和部署。建议密切监控资源使用情况。"
                    impact_text = "可能影响新应用部署和扩容"
                elif health == 'attention':
                    risk_level = '中等风险'
                    analysis_text = f"集群{cluster['name']}内存利用率为{memory_util:.1f}%，处于中等负载状态。当前运行{pods}个Pod在{nodes}个节点上，资源使用合理但需要持续关注。建议制定资源扩容计划。"
                    impact_text = "需要持续监控，适时调整"
                else:
                    risk_level = '低风险'
                    analysis_text = f"集群{cluster['name']}内存利用率为{memory_util:.1f}%，处于健康状态。当前运行{pods}个Pod在{nodes}个节点上，资源使用合理，运行稳定。"
                    impact_text = "运行稳定，无需特殊关注"

                html_content += f'''
                    <div class="cluster-analysis-card {health}">
                        <div class="cluster-name-analysis">{cluster['name']}</div>
                        <div class="risk-level {health}">{risk_level}</div>
                        <div class="analysis-text">{analysis_text}</div>
                        <div class="impact-text">影响评估：{impact_text}</div>
                    </div>'''
        html_content += '''</div>
                </div>'''
        # 添加建议部分
        recommendations_html = ''.join(
            [f'<div class="recommendation-item">• {rec}</div>' for rec in cluster_analysis.get('recommendations', [])])
        html_content += f'''
                <div class="report-section">
                    <h2 class="section-title">💡 优化建议</h2>
                    <div class="recommendations-box">
                        {recommendations_html}
                    </div>
                </div>
            </div>
        </div>

        <div id="storage" class="tab-content">
            <div class="cluster-grid">'''
        # 生成存储资源卡片
        for storage in storage_data:
            health = storage.get('storage_health', 'healthy')
            utilization = storage.get('storage_utilization', 0)
            note = storage.get('calculation_note', '')
            html_content += f'''
                <div class="cluster-card {health}">
                    <div class="cluster-header">
                        <div class="cluster-name">{storage['name']}</div>
                    </div>
                    <div class="cluster-body">
                        <div class="resource-item"><span class="resource-label">总容量</span><span class="resource-value">{storage.get('total_storage_capacity', 0):.0f} TB</span></div>
                        <div class="resource-item"><span class="resource-label">已使用</span><span class="resource-value">{storage.get('total_storage_used', 0):.0f} TB</span></div>
                        <div class="resource-item"><span class="resource-label">利用率</span><span class="resource-value">{utilization:.1f}%</span></div>
                        <div class="resource-item"><span class="resource-label">计算方式</span><span class="resource-value">{note}</span></div>
                    </div>
                </div>'''
        html_content += '''
            </div>
        </div>

        <div id="network" class="tab-content">
            <div class="cluster-grid">'''
        # 生成网络资源卡片
        for network in network_data:
            health = network.get('network_health', 'healthy')
            html_content += f'''
                <div class="cluster-card {health}">
                    <div class="cluster-header">
                        <div class="cluster-name">{network['name']}</div>
                    </div>
                    <div class="cluster-body">
                        <div class="resource-item"><span class="resource-label">带宽IN</span><span class="resource-value">{network.get('bandwidth_in_display', 'N/A')}</span></div>
                        <div class="resource-item"><span class="resource-label">带宽OUT</span><span class="resource-value">{network.get('bandwidth_out_display', 'N/A')}</span></div>
                        <div class="resource-item"><span class="resource-label">合计</span><span class="resource-value">{network.get('total_display', 'N/A')}</span></div>
                    </div>
                </div>'''
        html_content += '''
            </div>
        </div>

        <div id="instances" class="tab-content">
            <div class="charts-section">
                <div class="chart-container">
                    <div class="chart-title">实例类型分布</div>
                    <div class="chart-wrapper"><canvas id="instanceTypeChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">资源汇总统计</div>
                    <div class="chart-wrapper"><canvas id="resourceSummaryChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">GPU资源分布</div>
                    <div class="chart-wrapper"><canvas id="gpuDistributionChart"></canvas></div>
                </div>
                <div class="chart-container">
                    <div class="chart-title">内存资源占比</div>
                    <div class="chart-wrapper"><canvas id="memoryDistributionChart"></canvas></div>
                </div>
            </div>
            <div class="cluster-grid">'''
        # 生成BCC实例资源卡片
        if not bcc_data:
            html_content += '<div class="cluster-card healthy"><div class="cluster-header"><div class="cluster-name">⚠️ 未找到BCC实例数据</div></div><div class="cluster-body"><p>请检查Excel文件中是否包含"实例"工作表</p></div></div>'
        for bcc in bcc_data:
            gpu_count = int(bcc.get('gpu_count', 0))
            gpu_memory = float(bcc.get('gpu_memory', 0))
            gpu_info = ''
            if gpu_count > 0:
                gpu_info = f'''
                        <div class="resource-item"><span class="resource-label">GPU数量</span><span class="resource-value">{gpu_count} 块</span></div>
                        <div class="resource-item"><span class="resource-label">显存容量</span><span class="resource-value">{gpu_memory:.1f} GB</span></div>'''

            # --- 修改开始 ---
            # 为普通BCC实例添加分配率计算和显示
            if bcc['instance_type'] == '普通BCC实例':
                delivered_total = 25580
                total_used = 22605
                allocation_rate = (total_used / delivered_total * 100) if delivered_total > 0 else 0
                html_content += f'''
                <div class="cluster-card healthy">
                    <div class="cluster-header">
                        <div class="cluster-name">{bcc['name']}</div>
                    </div>
                    <div class="cluster-body">
                        <div class="resource-item"><span class="resource-label">交付总计</span><span class="resource-value">{delivered_total} c</span></div>
                        <div class="resource-item"><span class="resource-label">总使用</span><span class="resource-value">{total_used} c</span></div>
                        <div class="resource-item"><span class="resource-label">分配率</span><span class="resource-value">{allocation_rate:.2f}%</span></div>
                        <div class="resource-item"><span class="resource-label">实例类型</span><span class="resource-value">{bcc.get('instance_type', '普通实例')}</span></div>
                    </div>
                </div>'''
            else:
                html_content += f'''
                <div class="cluster-card healthy">
                    <div class="cluster-header">
                        <div class="cluster-name">{bcc['name']}</div>
                    </div>
                    <div class="cluster-body">
                        <div class="resource-item"><span class="resource-label">服务器数量</span><span class="resource-value">{bcc.get('server_count', 0)} 台</span></div>
                        <div class="resource-item"><span class="resource-label">CPU核数</span><span class="resource-value">{bcc.get('cpu_cores', 0)} 核</span></div>
                        <div class="resource-item"><span class="resource-label">可用内存</span><span class="resource-value">{bcc.get('memory_tb', 0):.1f} TB</span></div>{gpu_info}
                        <div class="resource-item"><span class="resource-label">实例类型</span><span class="resource-value">{bcc.get('instance_type', '普通实例')}</span></div>
                    </div>
                </div>'''
            # --- 修改结束 ---
        html_content += f'''
            </div>
        </div>

        <script>
        function openRuliu(name) {{
            // 使用如流协议打开联系人
            const infoflowUrl = 'infoflow://APICenter?data=eyJBUElOYW1lIjoiQmRIaUpzLnNlcnZpY2UuaG8ub3BlbiIsInZlcnNpb24iOiI2NSIsImRhdGEiOnsiaWQiOiIzMDAyNDI2MDY2IiwidHlwZSI6IjEiLCJzb3VyY2UiOiIxMDAwMiIsImFwcG5hbWUiOiLnn6Xor4blupMiLCJjb250ZXh0IjpbeyJ0eXBlIjoidXJsIiwiY29udGVudCI6Imh0dHBzOi8va3UuYmFpZHUtaW50LmNvbS9rbm93bGVkZ2UvSEZWckM3aHExUS8taWtvckZxZDVpLy1ab3oyN05CakMvd05nang5RjV6QlJxbmoifV19fQ%3D%3D';
            window.location.href = infoflowUrl;
        }}
        function showTab(tabName) {{
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(button => button.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        function filterClusters(health) {{
            const cards = document.querySelectorAll('#computeClusters .cluster-card');
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            cards.forEach(card => {{
                const cardHealth = card.getAttribute('data-health');
                if (health === 'all' || cardHealth === health) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
        function showMetricCategory(category) {{
            document.querySelectorAll('.metric-category').forEach(cat => cat.classList.remove('active'));
            document.querySelectorAll('.metric-cat-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(category + '-metrics').classList.add('active');
            event.target.classList.add('active');
        }}
        function openRuliu(name) {{
            // 使用如流协议打开联系人
            const infoflowUrl = 'infoflow://APICenter?data=eyJBUElOYW1lIjoiQmRIaUpzLnNlcnZpY2UuaG8ub3BlbiIsInZlcnNpb24iOiI2NSIsImRhdGEiOnsiaWQiOiIzMDAyNDI2MDY2IiwidHlwZSI6IjEiLCJzb3VyY2UiOiIxMDAwMiIsImFwcG5hbWUiOiLnn6Xor4blupMiLCJjb250ZXh0IjpbeyJ0eXBlIjoidXJsIiwiY29udGVudCI6Imh0dHBzOi8va3UuYmFpZHUtaW50LmNvbS9rbm93bGVkZ2UvSEZWckM3aHExUS8taWtvckZxZDVpLy1ab3oyN05CakMvd05nang5RjV6QlJxbmoifV19fQ%3D%3D';
            window.location.href = infoflowUrl;
        }}
        function showTab(tabName) {{
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(button => button.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        function filterClusters(health) {{
            const cards = document.querySelectorAll('#computeClusters .cluster-card');
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            cards.forEach(card => {{
                const cardHealth = card.getAttribute('data-health');
                if (health === 'all' || cardHealth === health) {{
                    card.style.display = 'block';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
        // 指标分析相关函数
        function showMetricCategory(category) {{
            document.querySelectorAll('.metric-category').forEach(cat => cat.classList.remove('active'));
            document.querySelectorAll('.metric-cat-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(category + '-metrics').classList.add('active');
            event.target.classList.add('active');
        }}
        
        function createMetricCard(metricName, analysis, clusterName) {{
            const status = analysis.status || 'unknown';
            const value = analysis.value || 'N/A';
            const message = analysis.message || '无数据';
            const thresholds = analysis.thresholds || {{}};
            
            let statusClass = status;
            let statusText = status === 'healthy' ? '正常' : 
                           status === 'warning' ? '警告' : 
                           status === 'critical' ? '严重' : '未知';
            
            let progressWidth = 0;
            if (typeof value === 'number' && thresholds.critical) {{
                progressWidth = Math.min((value / thresholds.critical) * 100, 100);
            }}
            
            return `
                <div class="metric-card">
                    <div class="metric-header">
                        <div class="metric-name">${{metricName}}</div>
                        <div class="metric-status ${{statusClass}}">${{statusText}}</div>
                    </div>
                    <div class="metric-value">${{typeof value === 'number' ? value.toFixed(1) : value}} ${{thresholds.unit || ''}}</div>
                    <div class="threshold-bar">
                        <div class="threshold-fill ${{statusClass}}" style="width: ${{progressWidth}}%"></div>
                    </div>
                    <div class="metric-threshold">${{message}}</div>
                </div>
            `;
        }}
        
        function populateAnomalyAlerts(metricsAnalysis) {{
            const criticalAlerts = document.getElementById('critical-alerts');
            const warningAlerts = document.getElementById('warning-alerts');
            
            let criticalCount = 0, warningCount = 0;
            
            console.log('填充异常告警，数据:', metricsAnalysis);
            
            Object.entries(metricsAnalysis).forEach(([cluster_id, analysis]) => {{
                console.log(`处理集群 ${{cluster_id}} 的异常信息:`, analysis.key_issues);
                
                analysis.key_issues.forEach(issue => {{
                    const alertHtml = `
                        <div class="alert-item ${{issue.status}}">
                            <div class="alert-metric">${{issue.metric}} <span class="alert-value">${{typeof issue.value === 'number' ? issue.value.toFixed(1) : issue.value}}</span></div>
                            <div class="alert-message">[集群: ${{cluster_id}}] ${{issue.message}}</div>
                        </div>
                    `;
                    
                    if (issue.status === 'critical') {{
                        criticalAlerts.innerHTML += alertHtml;
                        criticalCount++;
                    }} else if (issue.status === 'warning') {{
                        warningAlerts.innerHTML += alertHtml;
                        warningCount++;
                    }}
                }});
            }});
            
            console.log(`异常统计: 严重 ${{criticalCount}} 个，警告 ${{warningCount}} 个`);
            
            if (criticalCount === 0) {{
                criticalAlerts.innerHTML = '<div class="alert-item"><div class="alert-message">无严重异常</div></div>';
            }}
            if (warningCount === 0) {{
                warningAlerts.innerHTML = '<div class="alert-item"><div class="alert-message">无警告异常</div></div>';
            }}
        }}
        
        function validateMetricsData(metricsAnalysis) {{
            console.log('=== 指标数据验证 ===');
            if (!metricsAnalysis || Object.keys(metricsAnalysis).length === 0) {{
                console.error('指标分析数据为空！');
                return false;
            }}
            
            Object.entries(metricsAnalysis).forEach(([cluster_id, analysis]) => {{
                console.log(`集群 ${{cluster_id}}:`);
                console.log('  - 指标数量:', Object.keys(analysis.metrics_analysis).length);
                console.log('  - 关键问题:', analysis.key_issues.length);
                console.log('  - 状态统计:', analysis.summary);
                
                // 检查关键指标
                const keyMetrics = ['Memory Usage %', 'CPU Usage %', 'Node Ready Ratio'];
                keyMetrics.forEach(metric => {{
                    const value = analysis.metrics_analysis[metric];
                    if (value) {{
                        console.log(`  - ${{metric}}: ${{value.value}} (${{value.status}})`);
                    }} else {{
                        console.warn(`  - ${{metric}}: 数据缺失`);
                    }}
                }});
            }});
            
            return true;
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            // 指标分析数据
            const metricsAnalysis = {json.dumps(metrics_analysis)};
            
            // 填充原始数据表格
            function populateRawDataTable() {{
                const tableBody = document.getElementById('rawDataTableBody');
                if (!tableBody) return;
                
                Object.entries(metricsAnalysis).forEach(([clusterId, analysis]) => {{
                    const metrics = analysis.metrics_analysis;
                    
                    // 获取所有可用指标值
                    const nodeCount = metrics['Node Count']?.value || 0;
                    const podCount = metrics['Pod Count']?.value || 0;
                    const memoryUsage = metrics['Memory Usage %']?.value || 0;
                    const cpuUsage = metrics['CPU Usage %']?.value || 0;
                    const storageUsage = metrics['Node Filesystem Usage %']?.value || 0;
                    const memoryCapacity = (metrics['Memory Capacity']?.value || 0) / (1024**3); // 字节转GB
                    const memoryAllocatable = (metrics['Memory Allocatable']?.value || 0) / (1024**3); // 字节转GB
                    const memoryRequest = (metrics['Memory Request']?.value || 0) / (1024**3); // 字节转GB
                    const memoryUsageBytes = (metrics['Memory Usage']?.value || 0) / (1024**3); // 字节转GB
                    const cpuCapacity = metrics['CPU Capacity']?.value || 0;
                    const runningPods = metrics['Running Pod Count']?.value || 0;
                    const pendingPods = metrics['Pending Pod Count']?.value || 0;
                    const failedPods = metrics['Failed Pod Count']?.value || 0;
                    const podRestarts1h = metrics['Pod Restarts (1h)']?.value || 0;
                    const podRestarts24h = metrics['Pod Restarts (24h)']?.value || 0;
                    const containerRestarts = metrics['Container Restarts (1h)']?.value || 0;
                    const networkReceive = metrics['Network Receive Bytes/s']?.value || 0;
                    const networkTransmit = metrics['Network Transmit Bytes/s']?.value || 0;
                    const serviceCount = metrics['Service Count']?.value || 0;
                    const ingressCount = metrics['Ingress Count']?.value || 0;
                    const containerCount = metrics['Container Count']?.value || 0;
                    const podSuccessRate = metrics['Pod Success Rate']?.value || 0;
                    const readyNodes = metrics['Ready Node Count']?.value || 0;
                    const notReadyNodes = metrics['NotReady Node Count']?.value || 0;
                    
                    // 格式化网络流量显示
                    const formatBytes = (bytes) => {{
                        if (bytes === 0) return '0';
                        const k = 1024;
                        const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
                        const i = Math.floor(Math.log(bytes) / Math.log(k));
                        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
                    }};
                    
                    // 判断状态颜色
                    const getStatusClass = (value, type) => {{
                        if (type === 'usage') {{
                            if (value > 90) return 'status-critical';
                            if (value > 80) return 'status-warning';
                            return 'status-healthy';
                        }} else if (type === 'error') {{
                            if (value > 5) return 'status-critical';
                            if (value > 0) return 'status-warning';
                            return 'status-healthy';
                        }} else if (type === 'success') {{
                            if (value < 90) return 'status-critical';
                            if (value < 95) return 'status-warning';
                            return 'status-healthy';
                        }}
                        return '';
                    }};
                    
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="cluster-id">${{clusterId}}</td>
                        <td class="metric-value">${{nodeCount}}</td>
                        <td class="metric-value">${{podCount}}</td>
                        <td class="metric-value ${{getStatusClass(memoryUsage, 'usage')}}">${{memoryUsage.toFixed(1)}}%</td>
                        <td class="metric-value ${{getStatusClass(cpuUsage, 'usage')}}">${{cpuUsage.toFixed(1)}}%</td>
                        <td class="metric-value ${{getStatusClass(storageUsage, 'usage')}}">${{storageUsage.toFixed(1)}}%</td>
                        <td class="metric-value">${{memoryCapacity.toFixed(1)}}</td>
                        <td class="metric-value">${{memoryAllocatable.toFixed(1)}}</td>
                        <td class="metric-value">${{memoryRequest.toFixed(1)}}</td>
                        <td class="metric-value">${{memoryUsageBytes.toFixed(1)}}</td>
                        <td class="metric-value">${{cpuCapacity}}</td>
                        <td class="metric-value">${{runningPods}}</td>
                        <td class="metric-value ${{getStatusClass(pendingPods, 'error')}}">${{pendingPods}}</td>
                        <td class="metric-value ${{getStatusClass(failedPods, 'error')}}">${{failedPods}}</td>
                        <td class="metric-value ${{getStatusClass(podRestarts1h, 'error')}}">${{podRestarts1h}}</td>
                        <td class="metric-value ${{getStatusClass(podRestarts24h, 'error')}}">${{podRestarts24h}}</td>
                        <td class="metric-value ${{getStatusClass(containerRestarts, 'error')}}">${{containerRestarts}}</td>
                        <td class="metric-value">${{formatBytes(networkReceive)}}</td>
                        <td class="metric-value">${{formatBytes(networkTransmit)}}</td>
                        <td class="metric-value">${{serviceCount}}</td>
                        <td class="metric-value">${{ingressCount}}</td>
                        <td class="metric-value">${{containerCount}}</td>
                        <td class="metric-value ${{getStatusClass(podSuccessRate, 'success')}}">${{podSuccessRate.toFixed(1)}}%</td>
                        <td class="metric-value">${{readyNodes}}</td>
                        <td class="metric-value ${{getStatusClass(notReadyNodes, 'error')}}">${{notReadyNodes}}</td>
                    `;
                    tableBody.appendChild(row);
                }});
            }}
            
            // 执行表格填充
            populateRawDataTable();
            
            // 验证和填充指标数据
            if (validateMetricsData(metricsAnalysis)) {{
                populateAnomalyAlerts(metricsAnalysis);
                console.log('指标数据验证通过，开始创建图表');
            }} else {{
            }}
            
            // 计算实例资源统计数据
            const bccData = {json.dumps(bcc_data)};
            // --- 修改开始 ---
            // 为普通BCC实例使用写死的值，其他实例使用原有逻辑
            let totalServers = 0;
            let totalCpu = 0;
            let totalMemory = 0;
            let totalGpus = 0;
            let totalGpuMemory = 0;
            bccData.forEach(bcc => {{
                if (bcc.instance_type === '普通BCC实例') {{
                    totalServers += 25580;
                    totalCpu += 22605;
                    totalMemory += 22605;
                }} else {{
                    totalServers += bcc.server_count || 0;
                    totalCpu += bcc.cpu_cores || 0;
                    totalMemory += bcc.memory_tb || 0;
                    totalGpus += bcc.gpu_count || 0;
                    totalGpuMemory += bcc.gpu_memory || 0;
                }}
            }});
            // --- 修改结束 ---

            // 按实例类型分组统计
            const instanceTypes = {{}};
            bccData.forEach(bcc => {{
                const itype = bcc.instance_type || '普通BCC实例';
                if (!instanceTypes[itype]) {{
                    instanceTypes[itype] = {{servers: 0, gpus: 0, memory: 0}};
                }}
                if (itype === '普通BCC实例') {{
                    // 对于普通BCC，直接使用写死的值作为总计
                    instanceTypes[itype].servers = 25580;
                    instanceTypes[itype].gpus = 0; // 假设普通BCC无GPU
                    instanceTypes[itype].memory = 22605;
                }} else {{
                    instanceTypes[itype].servers += bcc.server_count || 0;
                    instanceTypes[itype].gpus += bcc.gpu_count || 0;
                    instanceTypes[itype].memory += bcc.memory_tb || 0;
                }}
            }});

            const typeNames = Object.keys(instanceTypes);
            const typeServers = typeNames.map(t => instanceTypes[t].servers);
            const typeGpus = typeNames.map(t => instanceTypes[t].gpus);
            const typeMemory = typeNames.map(t => instanceTypes[t].memory);

            // 实例类型分布图
            const instanceTypeCtx = document.getElementById('instanceTypeChart');
            if (instanceTypeCtx && typeof Chart !== 'undefined' && typeNames.length > 0) {{
                new Chart(instanceTypeCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: typeNames,
                        datasets: [{{
                            data: typeServers,
                            backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                            borderWidth: 3,
                            borderColor: 'rgba(255,255,255,0.8)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }}
                        }}
                    }}
                }});
            }}

            // 资源汇总统计图
            const resourceSummaryCtx = document.getElementById('resourceSummaryChart');
            if (resourceSummaryCtx && typeof Chart !== 'undefined') {{
                new Chart(resourceSummaryCtx, {{
                    type: 'bar',
                    data: {{
                        labels: ['服务器', 'CPU核数', '内存(TB)', 'GPU数量', 'GPU显存(GB)'],
                        datasets: [{{
                            label: '资源总量',
                            // --- 修改开始 ---
                            data: [totalServers, 22605, totalMemory, totalGpus, totalGpuMemory], // CPU核数强制为22605
                            // --- 修改结束 ---
                            backgroundColor: ['#1e293b', '#475569', '#64748b', '#94a3b8', '#cbd5e1'],
                            borderRadius: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}

            // GPU资源分布图
            const gpuDistributionCtx = document.getElementById('gpuDistributionChart');
            if (gpuDistributionCtx && typeof Chart !== 'undefined' && typeNames.length > 0) {{
                new Chart(gpuDistributionCtx, {{
                    type: 'bar',
                    data: {{
                        labels: typeNames,
                        datasets: [{{
                            label: 'GPU数量',
                            data: typeGpus,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderColor: 'rgba(16, 185, 129, 1)',
                            borderWidth: 2,
                            borderRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        scales: {{
                            x: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}

            // 内存资源占比图
            const memoryDistributionCtx = document.getElementById('memoryDistributionChart');
            if (memoryDistributionCtx && typeof Chart !== 'undefined' && typeNames.length > 0) {{
                new Chart(memoryDistributionCtx, {{
                    type: 'pie',
                    data: {{
                        labels: typeNames,
                        datasets: [{{
                            data: typeMemory,
                            backgroundColor: ['#6366f1', '#06b6d4', '#84cc16', '#f97316', '#ec4899'],
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'right' }}
                        }}
                    }}
                }});
            }}

            const healthCtx = document.getElementById('healthChart');
            if (healthCtx && typeof Chart !== 'undefined') {{
                new Chart(healthCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['健康', '注意', '警告', '严重'],
                        datasets: [{{
                            data: [{healthy_count}, {attention_count}, {warning_count}, {critical_count}],
                            backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#dc2626'],
                            borderWidth: 4,
                            borderColor: 'rgba(255,255,255,0.8)'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }}
                        }}
                    }}
                }});
            }}

            const overviewCtx = document.getElementById('overviewChart');
            if (overviewCtx && typeof Chart !== 'undefined') {{
                new Chart(overviewCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(cluster_names)},
                        datasets: [{{
                            label: '内存利用率 (%)',
                            data: {json.dumps(memory_utils)},
                            backgroundColor: 'rgba(30, 41, 59, 0.8)',
                            borderColor: 'rgba(30, 41, 59, 1)',
                            borderWidth: 3,
                            borderRadius: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}

            const nodeCtx = document.getElementById('nodeChart');
            if (nodeCtx && typeof Chart !== 'undefined') {{
                new Chart(nodeCtx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(cluster_names)},
                        datasets: [{{
                            label: '节点数量',
                            data: {json.dumps([c.get('total_nodes', 0) for c in compute_data])},
                            backgroundColor: 'rgba(71, 85, 105, 0.8)',
                            borderColor: 'rgba(71, 85, 105, 1)',
                            borderWidth: 3,
                            borderRadius: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        scales: {{
                            x: {{ beginAtZero: true }},
                            y: {{
                                ticks: {{
                                    font: {{ size: 10 }}
                                }}
                            }}
                        }}
                    }}
                }});
            }}

            const podCtx = document.getElementById('podChart');
            if (podCtx && typeof Chart !== 'undefined') {{
                new Chart(podCtx, {{
                    type: 'radar',
                    data: {{
                        labels: {json.dumps(cluster_names[:6])},
                        datasets: [{{
                            label: 'Pod数量',
                            data: {json.dumps([c.get('total_pods', 0) for c in compute_data[:6]])},
                            backgroundColor: 'rgba(30, 41, 59, 0.15)',
                            borderColor: 'rgba(30, 41, 59, 1)',
                            borderWidth: 3,
                            pointBackgroundColor: 'rgba(30, 41, 59, 1)',
                            pointBorderColor: 'rgba(255, 255, 255, 1)',
                            pointBorderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            r: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}
            
            // 创建指标分析图表
            createMetricsCharts(metricsAnalysis);
        }});
        
        function createMetricsCharts(metricsAnalysis) {{
            if (!metricsAnalysis || Object.keys(metricsAnalysis).length === 0) {{
                console.warn('指标分析数据为空，无法创建图表');
                return;
            }}
            
            console.log('开始创建指标图表，数据:', metricsAnalysis);
            
            // 计算异常指标统计数据
            let statsCritical = 0, statsWarning = 0, statsHealthy = 0;
            Object.values(metricsAnalysis).forEach(analysis => {{
                statsCritical += analysis.summary.critical || 0;
                statsWarning += analysis.summary.warning || 0;
                statsHealthy += analysis.summary.healthy || 0;
            }});
            
            // 提取所有集群的指标数据
            const clusterNames = Object.keys(metricsAnalysis);
            console.log('集群列表:', clusterNames);
            
            // 内存利用率分布
            const memoryUtils = clusterNames.map(cluster => {{
                const memUsage = metricsAnalysis[cluster].metrics_analysis['Memory Usage %'];
                const value = memUsage && typeof memUsage.value === 'number' ? memUsage.value : 0;
                console.log(`${{cluster}} 内存利用率:`, value);
                return value;
            }});
            console.log('所有集群内存利用率:', memoryUtils);
            
            const memoryUtilCtx = document.getElementById('memoryUtilChart');
            if (memoryUtilCtx && clusterNames.length > 0) {{
                console.log('创建内存利用率图表');
                new Chart(memoryUtilCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '内存利用率 (%)',
                            data: memoryUtils,
                            backgroundColor: memoryUtils.map(val => 
                                val >= 90 ? '#dc2626' : val >= 80 ? '#f59e0b' : '#10b981'
                            ),
                            borderRadius: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }},
                            title: {{
                                display: true,
                                text: `共 ${{clusterNames.length}} 个集群的内存利用率分布`
                            }}
                        }},
                        scales: {{
                            y: {{ 
                                beginAtZero: true,
                                max: 100,
                                ticks: {{
                                    callback: function(value) {{ return value + '%'; }}
                                }}
                            }}
                        }}
                    }}
                }});
            }} else {{
                console.warn('内存利用率图表创建失败: 元素不存在或数据为空');
            }}
            
            // CPU利用率分布
            const cpuUtils = clusterNames.map(cluster => {{
                const cpuUsage = metricsAnalysis[cluster].metrics_analysis['CPU Usage %'];
                return cpuUsage && typeof cpuUsage.value === 'number' ? cpuUsage.value : 0;
            }});
            
            const cpuUtilCtx = document.getElementById('cpuUtilChart');
            if (cpuUtilCtx) {{
                new Chart(cpuUtilCtx, {{
                    type: 'line',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: 'CPU利用率 (%)',
                            data: cpuUtils,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{ 
                                beginAtZero: true,
                                max: 100,
                                ticks: {{
                                    callback: function(value) {{ return value + '%'; }}
                                }}
                            }}
                        }}
                    }}
                }});
            }}
            
            // 容器重启统计
            const restartCounts = clusterNames.map(cluster => {{
                const restarts = metricsAnalysis[cluster].metrics_analysis['Pod Restarts (1h)'];
                return restarts && typeof restarts.value === 'number' ? restarts.value : 0;
            }});
            
            const restartCtx = document.getElementById('restartChart');
            if (restartCtx) {{
                new Chart(restartCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: 'Pod重启次数(1小时)',
                            data: restartCounts,
                            backgroundColor: restartCounts.map(val => 
                                val >= 20 ? '#dc2626' : val >= 10 ? '#f59e0b' : '#10b981'
                            ),
                            borderRadius: 6
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ display: false }}
                        }},
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}
            
            // 节点就绪率
            const nodeHealthScores = clusterNames.map(cluster => {{
                const healthScore = metricsAnalysis[cluster].metrics_analysis['Node Ready Ratio'];
                return healthScore && typeof healthScore.value === 'number' ? healthScore.value : 0;
            }});
            
            const nodeHealthCtx = document.getElementById('nodeHealthChart');
            if (nodeHealthCtx) {{
                new Chart(nodeHealthCtx, {{
                    type: 'radar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '节点就绪率',
                            data: nodeHealthScores,
                            backgroundColor: 'rgba(16, 185, 129, 0.2)',
                            borderColor: '#10b981',
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            r: {{
                                beginAtZero: true,
                                max: 100
                            }}
                        }}
                    }}
                }});
            }}
            
            // 存储利用率分布
            const storageUtils = clusterNames.map(cluster => {{
                const storage = metricsAnalysis[cluster].metrics_analysis['Node Filesystem Usage %'];
                return storage && typeof storage.value === 'number' ? storage.value : 0;
            }});
            
            const storageUtilCtx = document.getElementById('storageUtilChart');
            if (storageUtilCtx) {{
                new Chart(storageUtilCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            data: storageUtils,
                            backgroundColor: storageUtils.map(val => 
                                val >= 90 ? '#dc2626' : val >= 80 ? '#f59e0b' : '#10b981'
                            ),
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'right' }}
                        }}
                    }}
                }});
            }}
            
            // 资源效率对比 - 显示所有集群
            const efficiencyCtx = document.getElementById('efficiencyChart');
            if (efficiencyCtx) {{
                const datasets = clusterNames.map((cluster, i) => {{
                    const memReq = metricsAnalysis[cluster].metrics_analysis['Memory Request %'];
                    const cpuReq = metricsAnalysis[cluster].metrics_analysis['CPU Request %'];
                    const storage = metricsAnalysis[cluster].metrics_analysis['Node Filesystem Usage %'];
                    const health = metricsAnalysis[cluster].metrics_analysis['Node Ready Ratio'];
                    
                    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#dc2626', '#8b5cf6', '#06b6d4'];
                    const color = colors[i % colors.length];
                    
                    return {{
                        label: cluster,
                        data: [
                            memReq && typeof memReq.value === 'number' ? Math.min(memReq.value, 100) : 0,
                            cpuReq && typeof cpuReq.value === 'number' ? Math.min(cpuReq.value, 100) : 0,
                            storage && typeof storage.value === 'number' ? storage.value : 0,
                            health && typeof health.value === 'number' ? health.value : 0
                        ],
                        backgroundColor: color + '20',
                        borderColor: color,
                        borderWidth: 2
                    }};
                }});
                
                new Chart(efficiencyCtx, {{
                    type: 'radar',
                    data: {{
                        labels: ['内存请求率(%)', 'CPU请求率(%)', '存储使用率(%)', '节点健康度(%)'],
                        datasets: datasets
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            r: {{ beginAtZero: true, max: 100 }}
                        }},
                        plugins: {{
                            legend: {{ position: 'bottom', labels: {{ boxWidth: 12 }} }}
                        }}
                    }}
                }});
            }}
            
            // Pod成功率
            const podSuccessRates = clusterNames.map(cluster => {{
                const success = metricsAnalysis[cluster].metrics_analysis['Pod Success Rate'];
                return success && typeof success.value === 'number' ? success.value : 0;
            }});
            
            const podSuccessCtx = document.getElementById('podSuccessChart');
            if (podSuccessCtx) {{
                new Chart(podSuccessCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: 'Pod成功率 (%)',
                            data: podSuccessRates,
                            backgroundColor: podSuccessRates.map(val => 
                                val < 90 ? '#dc2626' : val < 95 ? '#f59e0b' : '#10b981'
                            ),
                            borderRadius: 8
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ display: false }} }},
                        scales: {{
                            y: {{ 
                                beginAtZero: true,
                                max: 100,
                                ticks: {{ callback: function(value) {{ return value + '%'; }} }}
                            }}
                        }}
                    }}
                }});
            }}
            
            // 节点压力状态
            const pressureData = clusterNames.map(cluster => {{
                const analysis = metricsAnalysis[cluster].metrics_analysis;
                return [
                    analysis['DiskPressure Node Count']?.value || 0,
                    analysis['MemoryPressure Node Count']?.value || 0,
                    analysis['PIDPressure Node Count']?.value || 0,
                    analysis['NotReady Node Count']?.value || 0
                ];
            }});
            
            const nodePressureCtx = document.getElementById('nodePressureChart');
            if (nodePressureCtx) {{
                new Chart(nodePressureCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '磁盘压力',
                            data: pressureData.map(d => d[0]),
                            backgroundColor: '#dc2626'
                        }}, {{
                            label: '内存压力',
                            data: pressureData.map(d => d[1]),
                            backgroundColor: '#f59e0b'
                        }}, {{
                            label: 'PID压力',
                            data: pressureData.map(d => d[2]),
                            backgroundColor: '#3b82f6'
                        }}, {{
                            label: '不可用节点',
                            data: pressureData.map(d => d[3]),
                            backgroundColor: '#8b5cf6'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{ y: {{ beginAtZero: true, stacked: true }}, x: {{ stacked: true }} }}
                    }}
                }});
            }}
            
            // 整体健康趋势
            const healthTrendCtx = document.getElementById('healthTrendChart');
            if (healthTrendCtx) {{
                new Chart(healthTrendCtx, {{
                    type: 'line',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '健康评分',
                            data: nodeHealthScores,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}, {{
                            label: 'Pod成功率',
                            data: podSuccessRates,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{ y: {{ beginAtZero: true, max: 100 }} }}
                    }}
                }});
            }}
            
            // 阈值违规分布
            const thresholdViolationCtx = document.getElementById('thresholdViolationChart');
            if (thresholdViolationCtx) {{
                new Chart(thresholdViolationCtx, {{
                    type: 'pie',
                    data: {{
                        labels: ['严重违规', '警告违规', '正常'],
                        datasets: [{{
                            data: [statsCritical || 0, statsWarning || 0, statsHealthy || 0],
                            backgroundColor: ['#dc2626', '#f59e0b', '#10b981'],
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{ legend: {{ position: 'bottom' }} }}
                    }}
                }});
            }}
            
            // 网络流量统计
            const networkReceive = clusterNames.map(cluster => {{
                const receive = metricsAnalysis[cluster].metrics_analysis['Network Receive Bytes/s'];
                return receive && typeof receive.value === 'number' ? (receive.value / 1024 / 1024).toFixed(2) : 0;
            }});
            
            const networkTransmit = clusterNames.map(cluster => {{
                const transmit = metricsAnalysis[cluster].metrics_analysis['Network Transmit Bytes/s'];
                return transmit && typeof transmit.value === 'number' ? (transmit.value / 1024 / 1024).toFixed(2) : 0;
            }});
            
            const networkTrafficCtx = document.getElementById('networkTrafficChart');
            if (networkTrafficCtx) {{
                new Chart(networkTrafficCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '接收流量(MB/s)',
                            data: networkReceive,
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderRadius: 4
                        }}, {{
                            label: '发送流量(MB/s)',
                            data: networkTransmit,
                            backgroundColor: 'rgba(16, 185, 129, 0.8)',
                            borderRadius: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}
            
            // 资源请求vs使用
            const memoryRatio = clusterNames.map(cluster => {{
                const ratio = metricsAnalysis[cluster].metrics_analysis['Memory Request vs Usage Ratio'];
                return ratio && typeof ratio.value === 'number' ? ratio.value : 0;
            }});
            
            const cpuRatio = clusterNames.map(cluster => {{
                const ratio = metricsAnalysis[cluster].metrics_analysis['CPU Request vs Usage Ratio'];
                return ratio && typeof ratio.value === 'number' ? ratio.value : 0;
            }});
            
            const requestUsageCtx = document.getElementById('requestUsageChart');
            if (requestUsageCtx) {{
                new Chart(requestUsageCtx, {{
                    type: 'line',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '内存效率(%)',
                            data: memoryRatio,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            tension: 0.4
                        }}, {{
                            label: 'CPU效率(%)',
                            data: cpuRatio,
                            borderColor: '#8b5cf6',
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}
            
            // 异常指标统计
            statsCritical = 0; statsWarning = 0; statsHealthy = 0;
            if (metricsAnalysis && Object.keys(metricsAnalysis).length > 0) {{
                Object.values(metricsAnalysis).forEach(analysis => {{
                    statsCritical += analysis.summary.critical || 0;
                    statsWarning += analysis.summary.warning || 0;
                    statsHealthy += analysis.summary.healthy || 0;
                }});
            }}
            
            const anomalyStatsCtx = document.getElementById('anomalyStatsChart');
            if (anomalyStatsCtx) {{
                new Chart(anomalyStatsCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['严重异常', '警告异常', '正常指标'],
                        datasets: [{{
                            data: [statsCritical || 0, statsWarning || 0, statsHealthy || 0],
                            backgroundColor: ['#dc2626', '#f59e0b', '#10b981'],
                            borderWidth: 3,
                            borderColor: '#ffffff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            title: {{
                                display: true,
                                text: `全部集群指标统计 (共${{statsCritical + statsWarning + statsHealthy}}个指标)`
                            }}
                        }}
                    }}
                }});
            }}
            
            // 服务组件统计图表
            const serviceStatsCtx = document.getElementById('serviceStatsChart');
            if (serviceStatsCtx) {{
                const serviceCounts = clusterNames.map(cluster => {{
                    const services = metricsAnalysis[cluster].metrics_analysis['Service Count'];
                    return services && typeof services.value === 'number' ? services.value : 0;
                }});
                
                const ingressCounts = clusterNames.map(cluster => {{
                    const ingress = metricsAnalysis[cluster].metrics_analysis['Ingress Count'];
                    return ingress && typeof ingress.value === 'number' ? ingress.value : 0;
                }});
                
                const nodeCounts = clusterNames.map(cluster => {{
                    const nodes = metricsAnalysis[cluster].metrics_analysis['Node Count'];
                    return nodes && typeof nodes.value === 'number' ? nodes.value : 0;
                }});
                
                new Chart(serviceStatsCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: 'Service数量',
                            data: serviceCounts,
                            backgroundColor: 'rgba(34, 197, 94, 0.8)',
                            borderRadius: 4
                        }}, {{
                            label: 'Ingress数量',
                            data: ingressCounts,
                            backgroundColor: 'rgba(245, 158, 11, 0.8)',
                            borderRadius: 4
                        }}, {{
                            label: 'Node数量',
                            data: nodeCounts,
                            backgroundColor: 'rgba(59, 130, 246, 0.8)',
                            borderRadius: 4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'top' }},
                            title: {{ display: true, text: '核心组件分布统计' }}
                        }},
                        scales: {{
                            y: {{ beginAtZero: true }}
                        }}
                    }}
                }});
            }}
            
            // 容器状态分布图表
            const containerStatsCtx = document.getElementById('containerStatsChart');
            if (containerStatsCtx) {{
                const runningPods = clusterNames.map(cluster => {{
                    const running = metricsAnalysis[cluster].metrics_analysis['Running Pod Count'];
                    return running && typeof running.value === 'number' ? running.value : 0;
                }});
                
                const succeededPods = clusterNames.map(cluster => {{
                    const succeeded = metricsAnalysis[cluster].metrics_analysis['Succeeded Pod Count'];
                    return succeeded && typeof succeeded.value === 'number' ? succeeded.value : 0;
                }});
                
                const failedPods = clusterNames.map(cluster => {{
                    const failed = metricsAnalysis[cluster].metrics_analysis['Failed Pod Count'];
                    return failed && typeof failed.value === 'number' ? failed.value : 0;
                }});
                
                new Chart(containerStatsCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['运行中Pod', '成功Pod', '失败Pod'],
                        datasets: [{{
                            data: [
                                runningPods.reduce((a, b) => a + b, 0),
                                succeededPods.reduce((a, b) => a + b, 0),
                                failedPods.reduce((a, b) => a + b, 0)
                            ],
                            backgroundColor: [
                                'rgba(34, 197, 94, 0.8)',
                                'rgba(59, 130, 246, 0.8)',
                                'rgba(239, 68, 68, 0.8)'
                            ],
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'bottom' }},
                            title: {{ display: true, text: '全集群Pod状态分布' }}
                        }}
                    }}
                }});
            }}
            
            // 资源容量对比图表
            const capacityComparisonCtx = document.getElementById('capacityComparisonChart');
            if (capacityComparisonCtx) {{
                const memoryCapacity = clusterNames.map(cluster => {{
                    const capacity = metricsAnalysis[cluster].metrics_analysis['Memory Capacity'];
                    return capacity && typeof capacity.value === 'number' ? (capacity.value / 1024 / 1024 / 1024).toFixed(1) : 0;
                }});
                
                const cpuCapacity = clusterNames.map(cluster => {{
                    const capacity = metricsAnalysis[cluster].metrics_analysis['CPU Capacity'];
                    return capacity && typeof capacity.value === 'number' ? capacity.value : 0;
                }});
                
                new Chart(capacityComparisonCtx, {{
                    type: 'bar',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '内存容量(GB)',
                            data: memoryCapacity,
                            backgroundColor: 'rgba(168, 85, 247, 0.8)',
                            borderRadius: 4,
                            yAxisID: 'y'
                        }}, {{
                            label: 'CPU容量(核)',
                            data: cpuCapacity,
                            backgroundColor: 'rgba(6, 182, 212, 0.8)',
                            borderRadius: 4,
                            yAxisID: 'y1'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'top' }},
                            title: {{ display: true, text: '集群资源容量对比' }}
                        }},
                        scales: {{
                            y: {{
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {{ display: true, text: '内存容量(GB)' }}
                            }},
                            y1: {{
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {{ display: true, text: 'CPU容量(核)' }},
                                grid: {{ drawOnChartArea: false }}
                            }}
                        }}
                    }}
                }});
            }}
            
            // Pod重启趋势图表
            const restartTrendCtx = document.getElementById('restartTrendChart');
            if (restartTrendCtx) {{
                const restarts1h = clusterNames.map(cluster => {{
                    const restarts = metricsAnalysis[cluster].metrics_analysis['Pod Restarts (1h)'];
                    return restarts && typeof restarts.value === 'number' ? restarts.value : 0;
                }});
                
                const restarts24h = clusterNames.map(cluster => {{
                    const restarts = metricsAnalysis[cluster].metrics_analysis['Pod Restarts (24h)'];
                    return restarts && typeof restarts.value === 'number' ? restarts.value : 0;
                }});
                
                new Chart(restartTrendCtx, {{
                    type: 'line',
                    data: {{
                        labels: clusterNames,
                        datasets: [{{
                            label: '1小时重启次数',
                            data: restarts1h,
                            borderColor: 'rgba(239, 68, 68, 1)',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }}, {{
                            label: '24小时重启次数',
                            data: restarts24h,
                            borderColor: 'rgba(245, 158, 11, 1)',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{ position: 'top' }},
                            title: {{ display: true, text: 'Pod重启趋势分析' }}
                        }},
                        scales: {{
                            y: {{ 
                                beginAtZero: true,
                                title: {{ display: true, text: '重启次数' }}
                            }}
                        }}
                    }}
                }});
            }}
        }}
        </script>
    </div>
</body>
</html>'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return output_path
    
    def _generate_metrics_summary(self, detailed_analysis: Dict) -> str:
        """生成关键指标摘要"""
        cluster_id = detailed_analysis.get('cluster_id', 'Unknown')
        metrics = detailed_analysis.get('metrics_analysis', {})
        
        # 提取关键指标
        mem_usage = metrics.get('Memory Usage %', {})
        cpu_usage = metrics.get('CPU Usage %', {})
        node_count = metrics.get('Node Count', {})
        pod_count = metrics.get('Pod Count', {})
        
        mem_val = self.safe_float(mem_usage.get('value', 0))
        cpu_val = self.safe_float(cpu_usage.get('value', 0))
        node_val = self.safe_int(node_count.get('value', 0))
        pod_val = self.safe_int(pod_count.get('value', 0))
        
        return f"节点:{node_val} | Pod:{pod_val} | 内存:{mem_val:.1f}% | CPU:{cpu_val:.1f}%"
    
    def _generate_cluster_detail_analysis(self, detailed_analysis: Dict) -> Dict:
        """生成集群详细分析"""
        cluster_id = detailed_analysis.get('cluster_id', 'Unknown')
        metrics = detailed_analysis.get('metrics_analysis', {})
        summary = detailed_analysis.get('summary', {})
        key_issues = detailed_analysis.get('key_issues', [])
        
        # 根据关键问题确定健康等级
        critical_count = summary.get('critical', 0)
        warning_count = summary.get('warning', 0)
        
        if critical_count > 0:
            health = 'critical'
            risk_level = '极高风险'
        elif warning_count >= 3:
            health = 'warning'
            risk_level = '高风险'
        elif warning_count > 0:
            health = 'attention'
            risk_level = '中等风险'
        else:
            health = 'healthy'
            risk_level = '低风险'
        
        # 生成分析文本
        analysis_parts = []
        impact_parts = []
        
        for issue in key_issues[:3]:  # 只取前3个关键问题
            analysis_parts.append(f"{issue.get('metric', '')}：{issue.get('message', '')}")
            
        if not analysis_parts:
            analysis_parts.append(f"集群{cluster_id}运行正常，各项指标处于健康状态。")
            impact_parts.append("运行稳定，无需特殊关注")
        else:
            impact_parts.append("需要密切关注并及时处理")
        
        return {
            'name': cluster_id,
            'health': health,
            'risk_level': risk_level,
            'analysis': ' | '.join(analysis_parts),
            'impact': '；'.join(impact_parts)
        }
