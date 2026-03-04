#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOS存储分析器
从Bos_used_v2.py迁移，保留完整逻辑
"""
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional


class BOSAnalyzer:
    """BOS对象存储分析器"""
    
    def __init__(self, bcm_client=None, user_id: str = "f008db4751894afe9b851e32a2068335"):
        """
        初始化BOS分析器
        
        Args:
            bcm_client: BCM客户端实例
            user_id: 百度云用户ID
        """
        self.client = bcm_client
        self.user_id = user_id
        self.scope = "BCE_BOS"
        self.region = "cd"
        self.metric_names = ["BucketObjectCount", "BucketSpaceUsedBytes"]
        self.statistics = ["maximum"]
        self.buckets = []
        self.progress_callback = None
    
    def load_buckets_from_file(self, file_path: str) -> List[str]:
        """
        从文件加载Bucket列表
        
        Args:
            file_path: Bucket列表文件路径
            
        Returns:
            Bucket名称列表
        """
        try:
            with open(file_path, 'r') as f:
                buckets = [line.strip() for line in f if line.strip()]
            print(f"从{file_path}加载了{len(buckets)}个Bucket")
            self.buckets = buckets
            return buckets
        except FileNotFoundError:
            print(f"文件{file_path}未找到")
            return []
    
    def load_buckets_from_list(self, buckets: List[str]):
        """
        从列表加载Bucket
        
        Args:
            buckets: Bucket名称列表
        """
        self.buckets = buckets
        print(f"加载了{len(buckets)}个Bucket")
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def get_bucket_metrics(self) -> List[Dict[str, Any]]:
        """
        获取所有Bucket的监控指标（并发处理）
        
        Returns:
            Bucket统计列表
        """
        if not self.client:
            raise Exception("BCM客户端未初始化")
        
        # UTC时间近一天的数据（结束时间不能晚于2小时前）
        now = datetime.now(timezone.utc)
        end_time = (now - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
        start_time = (now - timedelta(hours=27)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"查询时间范围: {start_time} 至 {end_time} (UTC)")
        
        results = []
        total_buckets = len(self.buckets)
        completed = 0
        
        # 使用线程池并发处理，提高速度
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        print_lock = threading.Lock()
        
        def process_bucket(idx_bucket):
            nonlocal completed
            idx, bucket = idx_bucket
            dimensions = [[{"name": "BucketId", "value": bucket}]]
            
            try:
                response = self.client.get_all_data_metrics_v2(
                    self.user_id, self.scope, self.region, dimensions, 
                    self.metric_names, self.statistics, start_time, end_time, 
                    type="Instance", cycle=3600
                )
                
                space_used = 0
                object_count = 0
                
                if hasattr(response, 'metrics'):
                    for metric in response.metrics:
                        if metric.metric_name == 'BucketSpaceUsedBytes' and metric.data_points:
                            space_used = max([p.maximum for p in metric.data_points if p.maximum is not None], default=0)
                        elif metric.metric_name == 'BucketObjectCount' and metric.data_points:
                            object_count = max([p.maximum for p in metric.data_points if p.maximum is not None], default=0)
                
                with print_lock:
                    completed += 1
                    print(f"[{completed}/{total_buckets}] {bucket}: {space_used / (1024**5):.6f} PB, {object_count:,} 文件")
                    if self.progress_callback:
                        self.progress_callback(completed, total_buckets, f"正在分析 {bucket} ({completed}/{total_buckets})")
                
                return {
                    'bucket': bucket,
                    'space': space_used,
                    'objects': object_count
                }
                
            except Exception as e:
                with print_lock:
                    completed += 1
                    print(f"[{completed}/{total_buckets}] 处理Bucket {bucket} 时出错: {e}")
                    if self.progress_callback:
                        self.progress_callback(completed, total_buckets, f"分析 {bucket} 失败 ({completed}/{total_buckets})")
                return {
                    'bucket': bucket,
                    'space': 0,
                    'objects': 0
                }
        
        # 使用20个线程并发处理
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(process_bucket, (idx, bucket)): bucket 
                      for idx, bucket in enumerate(self.buckets, 1)}
            
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def get_summary_stats(self, results: List[Dict]) -> Dict[str, Any]:
        """
        获取汇总统计
        
        Args:
            results: Bucket统计列表
            
        Returns:
            汇总统计字典
        """
        total_space = sum(r['space'] for r in results)
        total_objects = sum(r['objects'] for r in results)
        
        return {
            'total_buckets': len(results),
            'total_space_bytes': total_space,
            'total_space_pb': total_space / (1024**5),
            'total_objects': total_objects
        }
    
    def get_top30(self, results: List[Dict]) -> List[Dict]:
        """
        获取存储空间TOP30的Bucket
        
        Args:
            results: Bucket统计列表
            
        Returns:
            TOP30列表
        """
        sorted_results = sorted(results, key=lambda x: x['space'], reverse=True)
        top30 = sorted_results[:30]
        
        # 添加排名和PB单位
        for idx, item in enumerate(top30, 1):
            item['rank'] = idx
            item['space_pb'] = item['space'] / (1024**5)
        
        return top30
    
    def export_to_excel(self, results: List[Dict], filename: str = 'bos_storage_report.xlsx') -> str:
        """
        导出Excel报告
        
        Args:
            results: Bucket统计列表
            filename: 输出文件名
            
        Returns:
            生成的文件路径
        """
        summary = self.get_summary_stats(results)
        top30 = self.get_top30(results)
        
        # 准备数据
        df_all = pd.DataFrame(results)
        df_all['space_pb'] = df_all['space'] / (1024**5)
        
        df_top30 = pd.DataFrame(top30)
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # TOP30工作表
            df_top30[['rank', 'bucket', 'space_pb', 'objects']].to_excel(
                writer, sheet_name='TOP30', index=False,
                header=['排名', 'Bucket名称', '存储空间(PB)', '文件数量']
            )
            
            # 全部Bucket工作表
            df_all[['bucket', 'space_pb', 'objects']].to_excel(
                writer, sheet_name='全部Bucket', index=False,
                header=['Bucket名称', '存储空间(PB)', '文件数量']
            )
            
            # 汇总工作表
            summary_data = [
                ['总存储空间(PB)', summary['total_space_pb']],
                ['总文件数量', summary['total_objects']],
                ['Bucket总数', summary['total_buckets']]
            ]
            pd.DataFrame(summary_data, columns=['项目', '数值']).to_excel(
                writer, sheet_name='汇总', index=False
            )
        
        return filename
    
    def generate_html_report(self, results: List[Dict]) -> str:
        """
        生成HTML报告（完整保留原版格式）
        
        Args:
            results: Bucket统计列表
            
        Returns:
            HTML内容
        """
        summary = self.get_summary_stats(results)
        top30 = self.get_top30(results)
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建TOP30表格行
        top30_rows = ''
        for item in top30:
            top30_rows += f"<tr><td>{item['rank']}</td><td>{item['bucket']}</td><td>{item['space_pb']:.6f}</td><td>{item['objects']:,}</td></tr>"
        
        # 构建全部Bucket表格行
        all_rows = ''
        for result in results:
            space_pb = result['space'] / (1024**5)
            all_rows += f"<tr><td>{result['bucket']}</td><td>{space_pb:.6f}</td><td>{result['objects']:,}</td></tr>"
        
        # 准备Chart.js数据
        top30_labels = [item['bucket'] for item in top30]
        top30_data = [item['space_pb'] for item in top30]
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>BOS存储报表</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; }}
        th {{ background-color: #f2f2f2; }}
        .summary {{ background-color: #e6f3ff; font-weight: bold; }}
        .top-buckets {{ background-color: #fff2e6; }}
        h2 {{ color: #333; }}
        .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1>BOS存储空间报表</h1>
    <p>生成时间: {current_time}</p>
    
    <h2>存储空间使用量TOP30</h2>
    <div class="chart-container">
        <canvas id="top30Chart"></canvas>
    </div>
    <table>
        <tr class="top-buckets"><th>排名</th><th>Bucket名称</th><th>存储空间(PB)</th><th>文件数量</th></tr>
        {top30_rows}
    </table>
    
    <script>
    const ctx = document.getElementById('top30Chart').getContext('2d');
    const chart = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {top30_labels},
            datasets: [{{
                label: '存储空间(PB)',
                data: {top30_data},
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                y: {{
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: '存储空间(PB)'
                    }}
                }},
                x: {{
                    title: {{
                        display: true,
                        text: 'Bucket名称'
                    }},
                    ticks: {{
                        maxRotation: 45
                    }}
                }}
            }}
        }}
    }});
    </script>
    
    <h2>所有Bucket汇总</h2>
    <table>
        <tr><th>Bucket名称</th><th>存储空间(PB)</th><th>文件数量</th></tr>
        {all_rows}
        <tr class="summary"><td>总计</td><td>{summary['total_space_pb']:.6f}</td><td>{summary['total_objects']:,}</td></tr>
    </table>
</body>
</html>"""
        
        return html_content
    
    def analyze(self, buckets: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        执行完整的BOS存储分析
        
        Args:
            buckets: Bucket列表（可选）
            
        Returns:
            分析结果字典
        """
        if buckets:
            self.load_buckets_from_list(buckets)
        
        if not self.buckets:
            raise Exception("未加载任何Bucket")
        
        # 获取Bucket指标
        print("开始获取Bucket存储指标...")
        results = self.get_bucket_metrics()
        
        if not results:
            return {
                'success': False,
                'message': '未获取到任何Bucket数据',
                'bucket_count': len(self.buckets)
            }
        
        # 生成统计数据
        summary = self.get_summary_stats(results)
        top30 = self.get_top30(results)
        
        return {
            'success': True,
            'bucket_count': len(self.buckets),
            'summary': summary,
            'top30': top30,
            'all_buckets': results,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
