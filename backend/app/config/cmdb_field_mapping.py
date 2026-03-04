#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDB字段中文映射配置
"""

# 字段中文名称映射（175个字段）
FIELD_LABELS = {
    # BNS字段（7个）
    "bns_id": "BNS ID",
    "bns_serviceunit": "BNS服务单元",
    "bns_hostname": "BNS主机名",
    "bns_sn": "BNS序列号",
    "bns_ip": "BNS IP地址",
    "bns_instancename": "BNS实例名",
    "bns_product": "BNS产品",
    
    # RMS字段（37个）- 资源管理系统
    "rms_hostname": "RMS主机名",
    "rms_sn": "RMS序列号",
    "rms_cabinetsn": "机柜序列号",
    "rms_server_id": "服务器ID",
    "rms_suit": "服务器套件",
    "rms_type": "服务器类型",
    "rms_status": "服务器状态",
    "rms_arrive_time": "到货时间",
    "rms_online_time": "上线时间",
    "rms_mod_time": "修改时间",
    "rms_maintenance_time": "维保时间",
    "rms_model": "服务器型号",
    "rms_rack_info": "机架位置",
    "rms_manufacturer": "制造商",
    "rms_idc": "数据中心",
    "rms_product": "产品线",
    "rms_kernel": "内核版本",
    "rms_department": "所属部门",
    "rms_ilo_ip": "带外管理IP",
    "rms_ilo_mac": "带外管理MAC",
    "rms_ip_in1": "内网IP1",
    "rms_ip_in2": "内网IP2",
    "rms_ip_out": "外网IP",
    "rms_mac1": "MAC地址1",
    "rms_mac2": "MAC地址2",
    "rms_cpu": "CPU配置",
    "rms_flash": "Flash存储",
    "rms_harddisk": "硬盘配置",
    "rms_memory": "内存配置",
    "rms_networkcard": "网卡配置",
    "rms_raid": "RAID配置",
    "rms_ssd": "SSD配置",
    "rms_hwfailure_hostname": "硬件故障主机名",
    "rms_hwfailure_sn": "硬件故障序列号",
    "rms_hwfailure_devices": "故障设备",
    "rms_hwfailure_details": "故障详情",
    "rms_hwfailure_op_type": "故障操作类型",
    
    # Nova Host字段（101个）- OpenStack宿主机
    "nova_host_hypervisor_id": "虚拟化ID",
    "nova_host_hypervisor_hostname": "虚拟化主机名",
    "nova_host_cluster": "集群名称",
    "nova_host_node_type": "节点类型",
    "nova_host_node_state": "节点状态",
    "nova_host_azone": "可用区",
    "nova_host_group_id": "分组ID",
    "nova_host_model": "主机型号",
    "nova_host_logical_machine_suit": "逻辑机器套件",
    "nova_host_machine_suit": "物理机器套件",
    "nova_host_hypervisor_type": "虚拟化类型",
    "nova_host_physical_memory_mb_total": "物理内存总量(MB)",
    "nova_host_physical_memory_mb_free": "物理内存空闲(MB)",
    "nova_host_physical_disk_gb_free": "物理磁盘空闲(GB)",
    "nova_host_vcpus_total": "虚拟CPU总数",
    "nova_host_vcpus_used": "虚拟CPU已用",
    "nova_host_vcpus_free": "虚拟CPU空闲",
    "nova_host_running_vms": "运行中虚拟机数",
    "nova_host_physical_cpus": "物理CPU数",
    "nova_host_host_ip": "主机IP",
    "nova_host_hypervisor_version": "虚拟化版本",
    "nova_host_net_bandwidth_kbps": "网络带宽(Kbps)",
    "nova_host_blacklisted_expired_at": "黑名单过期时间",
    "nova_host_arrive_time": "到货时间",
    "nova_host_service_id": "服务ID",
    "nova_host_uuid": "主机UUID",
    "nova_host_user_id": "用户ID",
    "nova_host_cpu_allocation_ratio": "CPU分配比例",
    "nova_host_netbandwidth_allocation_ratio": "网络带宽分配比例",
    "nova_host_enable_dpdk": "启用DPDK",
    "nova_host_enable_numa": "启用NUMA",
    "nova_host_enable_turbo": "启用Turbo",
    "nova_host_enable_bind_core": "启用核心绑定",
    "nova_host_tor_ips": "TOR交换机IP",
    "nova_host_has_pci": "是否有PCI设备",
    "nova_host_cds_version": "CDS版本",
    "nova_host_cpuid_md5": "CPU ID MD5",
    "nova_host_qemu_version": "QEMU版本",
    "nova_host_libvirt_version": "Libvirt版本",
    "nova_host_kernel_version": "内核版本",
    "nova_host_net_bandwidth": "网络带宽",
    "nova_host_disk_bandwidth": "磁盘带宽",
    "nova_host_cpu_set": "CPU集合",
    "nova_host_vcpus_dedicated": "专用虚拟CPU",
    "nova_host_memory_mb_dedicated": "专用内存(MB)",
    "nova_host_local_gb_dedicated": "专用本地存储(GB)",
    "nova_host_project_id": "项目ID",
    "nova_host_name": "主机名称",
    "nova_host_blacklisted_description": "黑名单描述",
    "nova_host_blacklisted_reason": "黑名单原因",
    "nova_host_cpu_info": "CPU详细信息",
    "nova_host_scheduler_label": "调度标签",
    "nova_host_disks": "磁盘信息",
    "nova_host_pci_devices": "PCI设备",
    "nova_host_sn": "序列号",
    "nova_host_memory_mb": "内存(MB)",
    "nova_host_local_gb": "本地存储(GB)",
    "nova_host_ilo_ip": "带外管理IP",
    "nova_host_bond_mac": "Bond MAC地址",
    "nova_host_interfaces": "网络接口",
    "nova_host_tor_if": "TOR接口",
    "nova_host_tor_name": "TOR名称",
    "nova_host_created_at": "创建时间",
    "nova_host_updated_at": "更新时间",
    "nova_host_assigned_at": "分配时间",
    
    # Nova VM字段（30+个）- 虚拟机实例
    "nova_vm_instance_uuid": "实例UUID",
    "nova_vm_display_name": "显示名称",
    "nova_vm_hypervisor_hostname": "宿主机名",
    "nova_vm_cluster": "集群",
    "nova_vm_azone": "可用区",
    "nova_vm_user_id": "用户ID",
    "nova_vm_tenant_id": "租户ID",
    "nova_vm_metadata_source": "元数据来源",
    "nova_vm_os_type": "操作系统类型",
    "nova_vm_flavor_id": "规格ID",
    "nova_vm_vcpus": "虚拟CPU数",
    "nova_vm_memory_mb": "内存(MB)",
    "nova_vm_root_gb": "根磁盘(GB)",
    "nova_vm_ephemeral_gb": "临时磁盘(GB)",
    "nova_vm_hypervisor_dedicated": "专用虚拟化",
    "nova_vm_project_id": "项目ID",
    "nova_vm_instance_name": "实例名称",
    "nova_vm_image_uuid": "镜像UUID",
    "nova_vm_max_net_bandwidth_kbps": "最大网络带宽(Kbps)",
    "nova_vm_metadata_ephemeral_raw": "临时存储元数据",
    "nova_vm_metadata_root_on_cds_v2": "根磁盘在CDS V2",
    "nova_vm_metadata_root_on_cds": "根磁盘在CDS",
    "nova_vm_metadata_roc_status": "ROC状态",
    "nova_vm_power_state": "电源状态",
    "nova_vm_root_device_name": "根设备名",
    "nova_vm_root_volume_id": "根卷ID",
    "nova_vm_task_state": "任务状态",
    "nova_vm_vm_state": "虚拟机状态",
    "nova_vm_subnets": "子网",
    "nova_vm_floating_ips": "浮动IP",
    "nova_vm_fixed_ips": "固定IP",
    "nova_vm_virtual_disks": "虚拟磁盘",
    "nova_vm_volumes_attached": "挂载卷",
    "nova_vm_created_at": "创建时间",
    "nova_vm_updated_at": "更新时间",
    "nova_vm_launched_at": "启动时间",
    
    # Logical字段（15个）- 逻辑实例
    "logical_instance_id": "逻辑实例ID",
    "logical_instance_uuid": "逻辑实例UUID",
    "logical_region": "逻辑区域",
    "logical_deleted": "是否删除",
    "logical_roc_v2": "ROC V2",
    "logical_user_id": "逻辑用户ID",
    "logical_tenant_id": "逻辑租户ID",
    "logical_name": "逻辑名称",
    "logical_internal_ip": "内部IP",
    "logical_floating_ip": "浮动IP",
    "logical_status": "逻辑状态",
    "logical_order_uuid": "订单UUID",
    "logical_dcc_uuid": "DCC UUID",
    "logical_source": "来源",
    "logical_application": "应用",
    
    # CRM字段（15个）- 客户关系管理
    "crm_accountId": "账户ID",
    "crm_loginName": "登录名",
    "crm_registerTime": "注册时间",
    "crm_name": "账户名称",
    "crm_cname": "中文名称",
    "crm_serviceAccount": "服务账户",
    "crm_province": "省份",
    "crm_city": "城市",
    "crm_company": "公司名称",
    "crm_vip_type": "VIP类型",
    "crm_industry": "行业",
    "crm_industryDetail": "行业详情",
    "crm_accountManagers": "客户经理",
    "crm_techniqueAccountManagers": "技术客户经理",
    "crm_tags": "标签",
}

# 字段分组
FIELD_GROUPS = {
    "基础信息": ["bns_hostname", "rms_sn", "rms_status", "rms_type", "rms_manufacturer", "rms_idc"],
    "硬件配置": ["rms_cpu", "rms_memory", "rms_ssd", "rms_networkcard", "rms_rack_info"],
    "网络信息": ["rms_ip_in1", "rms_ip_in2", "rms_mac1", "rms_mac2", "rms_ilo_ip"],
    "虚拟化信息": ["nova_host_hypervisor_type", "nova_host_cluster", "nova_host_azone", "nova_host_node_type"],
    "资源使用": ["nova_host_vcpus_total", "nova_host_vcpus_used", "nova_host_physical_memory_mb_total", 
                 "nova_host_physical_memory_mb_free", "nova_host_running_vms"],
    "虚拟机信息": ["nova_vm_instance_uuid", "nova_vm_display_name", "nova_vm_vm_state", "nova_vm_vcpus", 
                   "nova_vm_memory_mb", "nova_vm_fixed_ips", "nova_vm_floating_ips"],
    "客户信息": ["crm_loginName", "crm_company", "crm_vip_type", "crm_accountManagers"],
    "时间信息": ["rms_arrive_time", "rms_online_time", "nova_vm_created_at", "nova_vm_launched_at"],
}

# 可搜索字段（支持关联搜索）
SEARCHABLE_FIELDS = {
    # 服务器相关
    "server": [
        "bns_hostname", "rms_sn", "rms_ip_in1", "rms_rack_info", 
        "nova_host_hypervisor_hostname", "nova_host_host_ip"
    ],
    # 虚拟机相关
    "instance": [
        "nova_vm_instance_uuid", "nova_vm_display_name", "nova_vm_fixed_ips", 
        "nova_vm_floating_ips", "nova_vm_instance_name"
    ],
    # 客户相关
    "customer": [
        "crm_loginName", "crm_company", "crm_accountId"
    ],
    # 硬件相关
    "hardware": [
        "rms_cpu", "rms_memory", "rms_ssd", "rms_manufacturer", "rms_model"
    ]
}

# 字段类型定义
FIELD_TYPES = {
    # 整数类型
    "integer": [
        "bns_id", "rms_server_id", "nova_host_physical_memory_mb_total",
        "nova_host_physical_memory_mb_free", "nova_host_physical_disk_gb_free",
        "nova_host_vcpus_total", "nova_host_vcpus_used", "nova_host_vcpus_free",
        "nova_host_running_vms", "nova_host_physical_cpus", "nova_vm_vcpus",
        "nova_vm_memory_mb", "nova_vm_root_gb", "nova_vm_ephemeral_gb",
        "nova_vm_power_state", "crm_serviceAccount"
    ],
    # 日期时间类型
    "datetime": [
        "rms_arrive_time", "rms_online_time", "rms_mod_time", "rms_maintenance_time",
        "nova_host_blacklisted_expired_at", "nova_host_arrive_time",
        "nova_host_created_at", "nova_host_updated_at", "nova_host_assigned_at",
        "nova_vm_created_at", "nova_vm_updated_at", "nova_vm_launched_at",
        "crm_registerTime"
    ],
    # JSON类型
    "json": [
        "nova_host_cpu_info", "nova_host_scheduler_label", "nova_host_disks",
        "nova_host_pci_devices", "nova_host_interfaces", "nova_host_tor_ips",
        "nova_vm_subnets", "nova_vm_floating_ips", "nova_vm_fixed_ips",
        "nova_vm_virtual_disks", "nova_vm_volumes_attached",
        "crm_accountManagers", "crm_techniqueAccountManagers", "crm_tags"
    ],
    # 文本类型
    "text": [
        "rms_cpu", "rms_memory", "rms_ssd", "rms_networkcard",
        "nova_host_blacklisted_description", "nova_host_cpu_info"
    ]
}

def get_field_label(field_name: str) -> str:
    """获取字段中文名称"""
    return FIELD_LABELS.get(field_name, field_name)

def get_searchable_fields() -> list:
    """获取所有可搜索字段"""
    all_fields = []
    for fields in SEARCHABLE_FIELDS.values():
        all_fields.extend(fields)
    return list(set(all_fields))

def get_field_type(field_name: str) -> str:
    """获取字段类型"""
    for field_type, fields in FIELD_TYPES.items():
        if field_name in fields:
            return field_type
    return "string"
