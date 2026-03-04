#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源分析服务
整合Prometheus数据和Excel数据进行综合分析
"""
import os
import sys
import json
from typing import Dict, Any, Optional
from pathlib import Path

# 添加legacy_modules到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'legacy_modules'))

from resource_analysis.analyzer import ResourceAnalyzer
from app.core.logger import logger
from app.services.prometheus_service import PrometheusService


async def analyze_resource_data(
    task_id: str,
    cluster_ids: Optional[list] = None,
    excel_file_path: Optional[str] = None,
    multicluster_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    执行资源分析
    
    Args:
        task_id: 任务ID
        cluster_ids: 集群ID列表（用于获取Prometheus数据）
        excel_file_path: Excel文件路径
        multicluster_file_path: Multi-Cluster JSON文件路径
        
    Returns:
        分析结果
    """
    try:
        logger.info(f"开始资源分析任务 {task_id}")
        
        # 创建分析器
        analyzer = ResourceAnalyzer()
        
        # 准备集群指标数据
        cluster_metrics_data = None
        actual_cluster_ids = []  # 记录实际采集的集群ID
        
        if cluster_ids:
            logger.info(f"获取 {len(cluster_ids)} 个集群的Prometheus指标数据")
            prometheus_service = PrometheusService()
            all_metrics = prometheus_service.get_multiple_clusters_metrics(cluster_ids)
            
            # 记录实际采集的集群ID（排除失败的）
            actual_cluster_ids = [cid for cid, metrics in all_metrics.items() if "error" not in metrics]
            
            cluster_metrics_data = {
                'timestamp': __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
                'requested_clusters': cluster_ids,  # 请求的集群列表
                'actual_clusters': actual_cluster_ids,  # 实际采集的集群列表
                'total_requested': len(cluster_ids),
                'total_actual': len(actual_cluster_ids),
                'clusters': all_metrics
            }
        
        # 执行分析
        logger.info("开始综合分析...")
        analysis_result = analyzer.analyze_files_integrated(
            multicluster_file_path=multicluster_file_path,
            excel_file_path=excel_file_path,
            cluster_metrics_data=cluster_metrics_data
        )
        
        # 生成HTML报告并上传到MinIO
        logger.info("生成HTML报告并上传到MinIO...")

        # 将all_cluster_data添加到analysis_result中（HTML生成需要）
        analysis_result['all_cluster_data'] = analyzer.all_cluster_data
        
        # 添加实际采集的集群信息
        if cluster_metrics_data:
            analysis_result['cluster_collection_info'] = {
                'requested_clusters': cluster_metrics_data['requested_clusters'],
                'actual_clusters': cluster_metrics_data['actual_clusters'],
                'total_requested': cluster_metrics_data['total_requested'],
                'total_actual': cluster_metrics_data['total_actual']
            }

        # 生成HTML到临时文件（带AI解读）
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp:
            tmp_html_path = tmp.name
            
            # 使用带AI解读的报告生成器
            try:
                from legacy_modules.resource_analysis.report_generator_with_ai import generate_resource_report_with_ai
                await generate_resource_report_with_ai(analyzer, analysis_result, tmp_html_path)
                logger.info("✅ 已生成包含 AI 解读的资源分析报告")
            except Exception as e:
                logger.warning(f"⚠️ 生成 AI 解读失败，使用基础报告: {e}")
                analyzer.generate_extended_html_report(analysis_result, tmp_html_path)

        # 上传到MinIO
        try:
            from app.services.report_upload_service import get_report_upload_service
            upload_service = get_report_upload_service()

            html_object_name, html_url = upload_service.upload_html_file(
                task_id=task_id,
                file_path=tmp_html_path,
                report_type='resource',
                delete_after_upload=False  # 先不删除，上传成功后再删除
            )

            logger.info(f"资源分析HTML报告已上传到MinIO: {html_object_name}")

            # 上传成功后手动删除临时文件
            try:
                if os.path.exists(tmp_html_path):
                    os.remove(tmp_html_path)
                    logger.info(f"已清理临时文件: {tmp_html_path}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            # 添加报告路径到结果中
            analysis_result['html_report'] = html_object_name
            analysis_result['html_report_url'] = html_url

        except Exception as e:
            logger.error(f"上传报告到MinIO失败: {e}")
            # 上传失败时也清理临时文件
            if os.path.exists(tmp_html_path):
                try:
                    os.remove(tmp_html_path)
                except:
                    pass
            raise
        
        logger.info(f"资源分析完成: {task_id}")
        
        return {
            'success': True,
            'task_id': task_id,
            'result': analysis_result
        }
        
    except Exception as e:
        logger.error(f"资源分析失败: {task_id}, 错误: {str(e)}")
        return {
            'success': False,
            'task_id': task_id,
            'error': str(e)
        }
