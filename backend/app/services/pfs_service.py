#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PFS 监控服务
提供 PFS 指标查询、统计分析、对比分析等功能
"""
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from app.core.pfs_prometheus_client import PFSPrometheusClient, METRIC_CONFIG
from app.core.redis_client import get_redis_client
from app.core.logger import logger
from app.models.pfs import (
    PFSMetric,
    PFSMetricResult,
    PFSMetricData,
    PFSMetricStatistics,
    PFSQueryRequest,
    PFSCompareRequest,
    MetricLevel,
    MetricCategory
)


class PFSService:
    """PFS 监控服务类"""
    
    def __init__(self, db_session: Session):
        """初始化服务
        
        Args:
            db_session: 数据库会话
        """
        self.pfs_client = PFSPrometheusClient(db_session)
        self.redis_client = get_redis_client()
        logger.info("✅ PFS 服务初始化完成")
    
    def get_metrics_catalog(self, level: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取指标目录（按分类分组）
        
        Args:
            level: 指标级别过滤 ("cluster" / "client" / None=全部)
        
        Returns:
            {
                "容量": [
                    {
                        "name": "FsUsage",
                        "zh_name": "文件系统已用容量",
                        "description": "...",
                        "unit": "bytes",
                        "level": "cluster",
                        "category": "容量"
                    },
                    ...
                ],
                "吞吐": [...],
                ...
            }
        """
        try:
            categories = defaultdict(list)
            
            for metric_name, config in METRIC_CONFIG.items():
                # 级别过滤
                if level and config.get("level") != level:
                    continue
                
                category = config.get("category", "其他")
                
                # 创建指标字典（直接返回字典，不使用Pydantic模型）
                metric_dict = {
                    "name": metric_name,
                    "zh_name": config.get("zh_name", metric_name),
                    "description": config.get("desc", ""),
                    "unit": config.get("unit", ""),
                    "unit_zh": config.get("unit_zh", ""),
                    "category": category,
                    "level": config.get("level", "cluster"),
                    "warn_threshold": config.get("warn_threshold"),
                    "critical_threshold": config.get("critical_threshold"),
                    "promql_template": config.get("promql_template", ""),
                    "normal_range": config.get("normal_range")
                }
                
                categories[category].append(metric_dict)
            
            logger.info(f"✅ 获取指标目录成功：{len(categories)} 个分类，共 {sum(len(v) for v in categories.values())} 个指标")
            return dict(categories)
            
        except Exception as e:
            logger.error(f"❌ 获取指标目录失败：{e}")
            raise
    
    def query_metrics_with_cache(
        self,
        request: PFSQueryRequest,
        use_cache: bool = True
    ) -> List[PFSMetricResult]:
        """
        查询指标数据（带 Redis 缓存）
        
        Args:
            request: 查询请求
            use_cache: 是否使用缓存
        
        Returns:
            指标结果列表
        """
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(request)
            
            # 尝试从缓存读取
            if use_cache:
                cached_data = self.redis_client.get_cache(cache_key)
                if cached_data:
                    logger.info(f"✅ 从缓存读取数据：{cache_key}")
                    return [PFSMetricResult(**item) for item in cached_data]
            
            # 执行查询
            results = self._query_metrics(request)
            
            # 写入缓存（5 分钟）
            if use_cache and results:
                # 检查结果类型，如果是 Pydantic 模型则转换为字典
                if isinstance(results[0], PFSMetricResult):
                    cache_data = [result.dict() for result in results]
                else:
                    cache_data = results  # 已经是字典列表
                self.redis_client.set_cache(cache_key, cache_data, expire=300)
                logger.info(f"✅ 查询结果已缓存：{cache_key}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 查询指标失败：{e}")
            raise
    
    def _query_metrics(self, request: PFSQueryRequest) -> List[PFSMetricResult]:
        """
        实际查询逻辑（无缓存）
        
        Args:
            request: 查询请求
        
        Returns:
            指标结果列表
        """
        results = []
        
        for metric_name in request.metrics:
            try:
                # 构建 PromQL
                promql = self._build_promql(
                    metric_name=metric_name,
                    level=request.level,
                    region=request.region,
                    instance_type=request.instance_type,
                    instance_id=request.instance_id,
                    client_id=request.client_id
                )
                
                logger.info(f"🔍 查询指标：{metric_name}, PromQL: {promql}")
                
                # 调用 Prometheus API
                prom_results = self.pfs_client.query_range(
                    promql=promql,
                    start_ts=request.start_time,
                    end_ts=request.end_time,
                    step=request.step
                )
                
                # 解析结果
                metric_result = self._parse_results(
                    metric_name=metric_name,
                    prom_results=prom_results,
                    request=request
                )
                
                if metric_result:
                    results.append(metric_result)
                
            except Exception as e:
                logger.error(f"❌ 查询指标 {metric_name} 失败：{e}")
                # 继续查询其他指标
                continue
        
        logger.info(f"✅ 查询完成：{len(results)}/{len(request.metrics)} 个指标成功")
        return results
    
    def _build_promql(
        self,
        metric_name: str,
        level: str,
        region: str,
        instance_type: str,
        instance_id: str,
        client_id: Optional[str] = None
    ) -> str:
        """
        构建 PromQL 查询语句
        
        Args:
            metric_name: 指标名称
            level: 指标级别 ("cluster" / "client")
            region: 区域
            instance_type: 实例类型
            instance_id: 实例 ID
            client_id: 客户端 ID（客户端级别必需）
        
        Returns:
            PromQL 查询语句
        """
        config = METRIC_CONFIG.get(metric_name, {})
        promql_template = config.get("promql_template", "")
        
        if not promql_template:
            # 降级：使用默认模板
            if level == "client":
                promql_template = f'{metric_name}{{region="$region", InstanceId="$instanceId", ClientId=~"$client"}}'
            else:
                promql_template = f'{metric_name}{{region="$region", InstanceId="$instanceId"}}'
        
        # 替换变量
        promql = promql_template.replace("$region", region)
        promql = promql.replace("$instanceType", instance_type)
        promql = promql.replace("$instanceId", instance_id)
        
        if level == "client" and client_id:
            # 精确匹配单个客户端，通配符才用正则匹配
            if client_id == ".*":
                promql = promql.replace("$client", client_id)
            else:
                # 将 ClientId=~"$client" 替换为精确匹配 ClientId="$client"
                promql = promql.replace('ClientId=~"$client"', f'ClientId="{client_id}"')
        
        return promql
    
    def _parse_results(
        self,
        metric_name: str,
        prom_results: List[Dict],
        request: PFSQueryRequest
    ) -> Optional[PFSMetricResult]:
        """
        解析 Prometheus 返回结果
        
        Args:
            metric_name: 指标名称
            prom_results: Prometheus 返回的原始结果
            request: 查询请求
        
        Returns:
            解析后的指标结果
        """
        if not prom_results:
            logger.warning(f"⚠️  指标 {metric_name} 无数据返回")
            return None
        
        config = METRIC_CONFIG.get(metric_name, {})
        all_data_points = []
        
        # 解析每个时间序列
        for series in prom_results:
            labels = series.get("metric", {})
            values = series.get("values", [])
            
            # 提取客户端信息（如果是客户端级别）
            client_id = labels.get("ClientId", "")
            client_ip = labels.get("ClientIp", "")
            
            # 解析数据点
            for timestamp, value in values:
                if value and value != "NaN":
                    try:
                        all_data_points.append(PFSMetricData(
                            timestamp=int(float(timestamp)),
                            value=float(value),
                            client_id=client_id if client_id else None,
                            client_ip=client_ip if client_ip else None,
                            labels=labels
                        ))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️  数据点解析失败：{e}")
                        continue
        
        if not all_data_points:
            logger.warning(f"⚠️  指标 {metric_name} 无有效数据点")
            return None
        
        # 计算统计值
        statistics = self._calculate_stats(all_data_points, config)
        
        # 构建结果
        return PFSMetricResult(
            metric_name=metric_name,
            zh_name=config.get("zh_name", metric_name),
            desc=config.get("desc", ""),
            unit=config.get("unit", ""),
            unit_zh=config.get("unit_zh", ""),
            level=config.get("level", "cluster"),
            category=config.get("category", "其他"),
            data_points=all_data_points,
            statistics=statistics,
            query_params={
                "region": request.region,
                "instance_id": request.instance_id,
                "client_id": request.client_id,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "step": request.step
            }
        )
    
    def _calculate_stats(
        self,
        data_points: List[PFSMetricData],
        config: Dict[str, Any]
    ) -> PFSMetricStatistics:
        """
        计算统计值
        
        Args:
            data_points: 数据点列表
            config: 指标配置
        
        Returns:
            统计结果
        """
        if not data_points:
            return PFSMetricStatistics(
                count=0,
                avg=0,
                min=0,
                max=0,
                p95=0,
                status="unknown"
            )
        
        values = [dp.value for dp in data_points]
        sorted_values = sorted(values)
        
        # 基础统计
        count = len(values)
        avg = sum(values) / count
        min_val = min(values)
        max_val = max(values)
        
        # P95 计算
        p95_idx = int(count * 0.95)
        p95 = sorted_values[p95_idx] if count >= 20 else max_val
        
        # 状态判断
        status = self._determine_status(avg, max_val, config)
        
        return PFSMetricStatistics(
            count=count,
            avg=avg,
            min=min_val,
            max=max_val,
            p95=p95,
            status=status
        )
    
    def _determine_status(
        self,
        avg_value: float,
        max_value: float,
        config: Dict[str, Any]
    ) -> str:
        """
        判断指标状态
        
        Args:
            avg_value: 平均值
            max_value: 最大值
            config: 指标配置
        
        Returns:
            状态：normal / warning / critical
        """
        critical_threshold = config.get("critical_threshold")
        warn_threshold = config.get("warn_threshold")
        unit = config.get("unit", "")
        
        # 延迟类指标（值越大越差）
        if "µs" in unit or "Latency" in config.get("metric_name", ""):
            if critical_threshold and max_value > critical_threshold:
                return "critical"
            elif warn_threshold and max_value > warn_threshold:
                return "warning"
        
        # 百分比类指标（值越大越差）
        elif "percent" in unit.lower() or "%" in config.get("unit_zh", ""):
            if critical_threshold and avg_value > critical_threshold:
                return "critical"
            elif warn_threshold and avg_value > warn_threshold:
                return "warning"
        
        # 吞吐/QPS 类指标（值下降超过阈值为异常）
        elif "Bps" in unit or "ops" in unit or "iops" in unit:
            if critical_threshold and critical_threshold < 0:
                # 负数阈值表示下降百分比（如 -0.90 表示下降 90%）
                # 这里需要历史基线数据，暂时不实现
                pass
        
        return "normal"
    
    def compare_metrics(
        self,
        request: PFSCompareRequest
    ) -> Dict[str, Any]:
        """
        对比分析（今天 vs 昨天同期）
        
        Args:
            request: 对比请求
        
        Returns:
            对比结果
        """
        try:
            # 计算时间范围
            end_today = int(datetime.now().timestamp())
            start_today = end_today - request.time_range_hours * 3600
            
            end_yesterday = end_today - 24 * 3600
            start_yesterday = start_today - 24 * 3600
            
            logger.info(f"📊 对比分析：今天 {datetime.fromtimestamp(start_today)} ~ {datetime.fromtimestamp(end_today)}")
            logger.info(f"📊 对比分析：昨天 {datetime.fromtimestamp(start_yesterday)} ~ {datetime.fromtimestamp(end_yesterday)}")
            
            # 查询今天数据
            today_request = PFSQueryRequest(
                metrics=request.metrics,
                level=request.level,
                region=request.region,
                instance_type=request.instance_type,
                instance_id=request.instance_id,
                client_id=request.client_id,
                start_time=start_today,
                end_time=end_today,
                step=request.step
            )
            today_results = self.query_metrics_with_cache(today_request, use_cache=False)
            
            # 查询昨天数据
            yesterday_request = PFSQueryRequest(
                metrics=request.metrics,
                level=request.level,
                region=request.region,
                instance_type=request.instance_type,
                instance_id=request.instance_id,
                client_id=request.client_id,
                start_time=start_yesterday,
                end_time=end_yesterday,
                step=request.step
            )
            yesterday_results = self.query_metrics_with_cache(yesterday_request, use_cache=False)
            
            # 构建对比结果
            comparison = self._build_comparison(today_results, yesterday_results)
            
            logger.info(f"✅ 对比分析完成：{len(comparison)} 个指标")
            return comparison
            
        except Exception as e:
            logger.error(f"❌ 对比分析失败：{e}")
            raise
    
    def _build_comparison(
        self,
        today_results: List[PFSMetricResult],
        yesterday_results: List[PFSMetricResult]
    ) -> Dict[str, Any]:
        """
        构建对比结果
        
        Args:
            today_results: 今天的查询结果
            yesterday_results: 昨天的查询结果
        
        Returns:
            对比结果字典
        """
        comparison = {
            "summary": {
                "total_metrics": len(today_results),
                "stable_count": 0,
                "warning_count": 0,
                "critical_count": 0
            },
            "metrics": []
        }
        
        # 构建昨天数据的映射
        yesterday_map = {result.metric_name: result for result in yesterday_results}
        
        for today_result in today_results:
            metric_name = today_result.metric_name
            yesterday_result = yesterday_map.get(metric_name)
            
            if not yesterday_result:
                logger.warning(f"⚠️  指标 {metric_name} 昨天无数据，跳过对比")
                continue
            
            # 计算变化率
            today_avg = today_result.statistics.avg
            yesterday_avg = yesterday_result.statistics.avg
            
            if yesterday_avg != 0:
                change_percent = (today_avg - yesterday_avg) / abs(yesterday_avg) * 100
            else:
                change_percent = 0
            
            # 判断变化状态
            if abs(change_percent) > 50:
                change_status = "critical"
                comparison["summary"]["critical_count"] += 1
            elif abs(change_percent) > 20:
                change_status = "warning"
                comparison["summary"]["warning_count"] += 1
            else:
                change_status = "stable"
                comparison["summary"]["stable_count"] += 1
            
            # 添加对比结果
            comparison["metrics"].append({
                "metric_name": metric_name,
                "zh_name": today_result.zh_name,
                "unit_zh": today_result.unit_zh,
                "category": today_result.category,
                "today": {
                    "avg": today_avg,
                    "max": today_result.statistics.max,
                    "min": today_result.statistics.min,
                    "status": today_result.statistics.status,
                    "data_points": [
                        {
                            "timestamp": point.timestamp,
                            "value": point.value
                        }
                        for point in today_result.data_points
                    ]
                },
                "yesterday": {
                    "avg": yesterday_avg,
                    "max": yesterday_result.statistics.max,
                    "min": yesterday_result.statistics.min,
                    "status": yesterday_result.statistics.status,
                    "data_points": [
                        {
                            "timestamp": point.timestamp,
                            "value": point.value
                        }
                        for point in yesterday_result.data_points
                    ]
                },
                "change": {
                    "percent": change_percent,
                    "status": change_status,
                    "direction": "up" if change_percent > 0 else "down" if change_percent < 0 else "stable"
                }
            })
        
        return comparison
    
    def _generate_cache_key(self, request: PFSQueryRequest) -> str:
        """
        生成缓存键
        
        Args:
            request: 查询请求
        
        Returns:
            缓存键字符串
        """
        # 构建缓存键的组成部分
        key_parts = [
            "pfs:query",
            ",".join(sorted(request.metrics)),
            request.level,
            request.region,
            request.instance_id,
            request.client_id or "all",
            str(request.start_time),
            str(request.end_time),
            request.step
        ]
        
        # 生成 MD5 哈希（避免键过长）
        key_str = ":".join(key_parts)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        return f"pfs:query:{key_hash}"
