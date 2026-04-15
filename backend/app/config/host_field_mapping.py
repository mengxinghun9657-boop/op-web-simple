# -*- coding: utf-8 -*-
"""
宿主机数据库字段映射配置
用于将中文字段名映射为更易理解的描述，提升 Schema RAG 检索效果
"""

# 宿主机数据库字段映射
HOST_FIELD_MAPPING = {
    # mydb.bce_cce_nodes - CCE集群节点信息（最重要！）
    "bce_cce_nodes": {
        "cluster_id": "集群ID（CCE集群唯一标识）",
        "collect_date": "数据采集日期",
        "insert_time": "数据插入时间",
        "节点名称": "节点名称（节点IP地址）",
        "实例名称_id": "实例名称和ID（格式：名称 / 实例ID）",
        "状态": "节点状态（可用/不可用）",
        "支付方式": "付费方式（后付费/预付费）",
        "可用区": "可用区（如：可用区C）",
        "ip地址": "节点IP地址（私网IP）",
        "配置_类型": "节点配置规格（CPU核数/内存/磁盘/规格）",
        "加速芯片类型": "GPU型号（如：nTeslaH20）",
        "加速芯片（已使用_总卡数）": "GPU使用情况（已使用/总卡数）",
        "空闲加速芯片卡数": "空闲GPU卡数",
        "资源申请_|_限制": "CPU和内存的申请率和限制率",
        "容器组（已分配_总额度）": "Pod分配情况（已分配/总额度）",
        "节点组": "节点组名称",
        "超节点": "超节点信息",
        "kubelet版本_runtime版本_os版本": "Kubernetes版本信息",
        "创建时间": "节点创建时间",
        "table_purpose": "【核心表】CCE集群节点信息表。专门用于通过【IP地址】或【节点名称】查询其所属的【集群ID(cluster_id)】。包含实例ID、状态、GPU型号等硬件信息。适用场景：根据IP地址查询集群、查询节点配置、GPU资源统计。"
    },
    
    # mydb.bce_bcc_instances - BCC实例信息
    "bce_bcc_instances": {
        "id": "记录ID",
        "collect_date": "数据采集日期",
        "insert_time": "数据插入时间",
        "bcc_id": "BCC实例ID（唯一标识）",
        "名称": "实例名称",
        "标签": "实例标签（包含环境、项目、申请人等信息）",
        "描述": "实例描述",
        "状态": "实例状态（运行中/已停止等）",
        "gpu型号": "GPU型号",
        "gpu数量": "GPU卡数",
        "gpu显存": "GPU显存大小",
        "实例规格": "实例规格（如：bcc.g4.c84m352）",
        "内网ip": "主私网IP地址",
        "公网ip": "主公网IP地址",
        "弹性网卡数量": "弹性网卡数量",
        "ipv6地址": "IPv6地址",
        "cpu（核）": "CPU核数",
        "内存（gb）": "内存大小（GB）",
        "系统盘（gb）": "系统盘大小（GB）",
        "操作系统名称": "操作系统名称",
        "操作系统版本": "操作系统版本",
        "支付方式": "付费方式",
        "所在网络": "VPC网络",
        "所在子网": "子网",
        "创建时间": "实例创建时间",
        "到期时间": "实例到期时间",
        "地域": "地域",
        "可用区": "可用区",
        "密钥对id": "密钥对ID",
        "密钥对名称": "密钥对名称",
        "table_purpose": "BCC实例信息表，包含实例的详细配置和IP地址"
    },
    
    # mydb.cluster_stats - 集群统计信息
    "cluster_stats": {
        "cluster_id": "集群ID",
        "collect_date": "统计日期",
        "memory_capacity": "内存总容量（字节）",
        "memory_request": "内存请求量（字节）",
        "memory_limit": "内存限制量（字节）",
        "memory_usage": "内存使用量（字节）",
        "cpu_capacity": "CPU总容量（核）",
        "node_count": "节点总数",
        "cpu_allocatable": "CPU可分配量（核）",
        "cpu_request": "CPU请求量（核）",
        "cpu_limit": "CPU限制量（核）",
        "pod_count": "Pod总数",
        "cpu_usage": "CPU使用量（核）",
        "running_pod_count": "运行中的Pod数量",
        "pending_pod_count": "等待中的Pod数量",
        "memory_allocatable": "内存可分配量（字节）",
        "failed_pod_count": "失败的Pod数量",
        "succeeded_pod_count": "成功的Pod数量",
        "pod_restarts_1h": "1小时内Pod重启次数",
        "ready_node_count": "就绪节点数量",
        "evicted_pod_count": "被驱逐的Pod数量",
        "notready_node_count": "未就绪节点数量",
        "pod_restarts_24h": "24小时内Pod重启次数",
        "insert_time": "数据插入时间",
        "table_purpose": "集群资源统计信息表，包含CPU、内存、Pod等统计数据"
    },
    
    # bcc_monitor.bcc_instances - BCC实例监控
    "bcc_instances": {
        "instance_id": "BCC实例ID",
        "instance_name": "实例名称",
        "status": "监控状态（active/inactive）",
        "created_at": "记录创建时间",
        "updated_at": "记录更新时间",
        "table_purpose": "BCC实例监控配置表"
    },
    
    # bcc_monitor.bcc_metrics - BCC监控指标
    "bcc_metrics": {
        "id": "记录ID",
        "instance_id": "BCC实例ID",
        "metric_type": "指标类型（cpu_usage/mem_usage）",
        "metric_value": "指标值（百分比）",
        "timestamp": "数据时间戳",
        "created_at": "记录创建时间",
        "table_purpose": "BCC实例监控指标数据表（CPU、内存使用率）"
    },
    
    # bcc_monitor.bcc_daily_summary - BCC日统计
    "bcc_daily_summary": {
        "id": "记录ID",
        "date": "统计日期",
        "instance_id": "BCC实例ID",
        "avg_cpu": "平均CPU使用率",
        "max_cpu": "最高CPU使用率",
        "min_cpu": "最低CPU使用率",
        "avg_mem": "平均内存使用率",
        "max_mem": "最高内存使用率",
        "min_mem": "最低内存使用率",
        "created_at": "记录创建时间",
        "table_purpose": "BCC实例每日监控统计数据"
    },
    
    # bos_monitoring.bos_metrics - BOS监控指标
    "bos_metrics": {
        "id": "记录ID",
        "bucket_name": "Bucket名称",
        "space_used_bytes": "存储空间使用量（字节）",
        "object_count": "文件数量",
        "space_used_tb": "存储空间使用量（TB）",
        "data_date": "数据日期",
        "timestamp": "数据时间戳",
        "created_at": "记录创建时间",
        "updated_at": "记录更新时间",
        "table_purpose": "BOS存储监控指标数据表"
    },
    
    # bos_monitoring.bos_summary - BOS汇总统计
    "bos_summary": {
        "id": "记录ID",
        "data_date": "数据日期",
        "total_buckets": "Bucket总数",
        "total_space_bytes": "总存储空间（字节）",
        "total_space_tb": "总存储空间（TB）",
        "total_objects": "总文件数量",
        "timestamp": "数据时间戳",
        "created_at": "记录创建时间",
        "updated_at": "记录更新时间",
        "table_purpose": "BOS存储汇总统计数据表"
    },
    
    # gpu_monitoring.gpu_metrics - GPU监控指标
    "gpu_metrics": {
        "id": "记录ID",
        "instance_id": "GPU实例ID",
        "metric_type": "指标类型（gpu_utilization/memory_utilization/ecc_errors/temperature/status）",
        "metric_value": "指标值",
        "timestamp": "数据时间戳",
        "data_date": "数据日期",
        "created_at": "记录创建时间",
        "table_purpose": "GPU监控指标数据表"
    },
    
    # gpu_monitoring.gpu_daily_summary - GPU日统计
    "gpu_daily_summary": {
        "id": "记录ID",
        "instance_id": "GPU实例ID",
        "data_date": "数据日期",
        "avg_gpu_utilization": "平均GPU利用率",
        "max_gpu_utilization": "最大GPU利用率",
        "min_gpu_utilization": "最小GPU利用率",
        "avg_memory_utilization": "平均内存利用率",
        "max_memory_utilization": "最大内存利用率",
        "total_ecc_errors": "ECC错误总数",
        "max_temperature": "最高温度",
        "avg_temperature": "平均温度",
        "created_at": "记录创建时间",
        "updated_at": "记录更新时间",
        "table_purpose": "GPU每日监控统计数据"
    },
    
    # gpu_monitoring.gpu_aggregate_summary - GPU汇聚统计
    "gpu_aggregate_summary": {
        "id": "记录ID",
        "data_date": "数据日期",
        "total_instances": "GPU实例总数",
        "avg_gpu_utilization": "所有GPU平均利用率",
        "avg_memory_utilization": "所有GPU平均内存利用率",
        "total_ecc_errors": "ECC错误总数",
        "max_temperature": "最高温度",
        "high_util_instances": "高负载实例数（>80%）",
        "error_instances": "ECC错误实例数",
        "created_at": "记录创建时间",
        "updated_at": "记录更新时间",
        "table_purpose": "GPU汇聚统计数据表"
    },
    
    # gpu_stats.gpu_period_summary - GPU时段统计
    "gpu_period_summary": {
        "id": "记录ID",
        "period_name": "时间段名称",
        "start_time": "开始时间",
        "end_time": "结束时间",
        "h800_hours": "H800卡时",
        "l20_hours": "L20卡时",
        "h20_hours": "H20卡时",
        "total_hours": "总卡时",
        "collect_time": "采集时间",
        "table_purpose": "GPU时段统计数据表（卡时统计）"
    },
    
    # gpu_stats.gpu_pod_detail - GPU Pod详情
    "gpu_pod_detail": {
        "id": "记录ID",
        "period_name": "时间段名称",
        "start_time": "开始时间",
        "end_time": "结束时间",
        "namespace": "命名空间",
        "pod_name": "Pod名称",
        "gpu_model": "GPU型号",
        "gpu_count": "GPU卡数",
        "card_hours": "卡时",
        "collect_time": "采集时间",
        "table_purpose": "GPU Pod详细信息表（Pod级别的GPU使用统计）"
    },
}

# 数据库用途说明
DATABASE_PURPOSE = {
    "mydb": "主数据库，包含BCC实例、CCE节点、集群统计等核心数据",
    "bcc_monitor": "BCC实例监控数据库，包含CPU、内存等监控指标",
    "bos_monitoring": "BOS对象存储监控数据库，包含存储空间、文件数量等指标",
    "gpu_monitoring": "GPU监控数据库，包含GPU利用率、温度、ECC错误等指标",
    "gpu_stats": "GPU统计数据库，包含GPU卡时统计、Pod级别的GPU使用情况",
    "h20_l20_gpu_monitoring": "H20/L20 GPU专用监控数据库",
}

# 常用查询场景与表的映射
QUERY_SCENARIOS = {
    "实例IP查集群": ["bce_cce_nodes"],  # 最常用！
    "实例ID查信息": ["bce_bcc_instances", "bce_cce_nodes"],
    "集群资源统计": ["cluster_stats"],
    "BCC监控数据": ["bcc_metrics", "bcc_daily_summary"],
    "GPU监控数据": ["gpu_metrics", "gpu_daily_summary", "gpu_aggregate_summary"],
    "GPU卡时统计": ["gpu_period_summary", "gpu_pod_detail"],
    "BOS存储统计": ["bos_metrics", "bos_summary"],
}
