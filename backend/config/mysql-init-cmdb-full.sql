-- ============================================
-- CMDB完整表结构初始化脚本
-- 支持175个字段的完整CMDB数据模型
-- ============================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 删除旧表（如果存在）
DROP TABLE IF EXISTS `iaas_instances`;
DROP TABLE IF EXISTS `iaas_servers`;

-- ============================================
-- CMDB物理服务器表（完整版 - 175个字段）
-- ============================================
CREATE TABLE `iaas_servers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    -- ========== BNS字段（7个）==========
    `bns_id` INT COMMENT 'BNS ID',
    `bns_serviceunit` VARCHAR(255) COMMENT 'BNS服务单元',
    `bns_hostname` VARCHAR(255) UNIQUE COMMENT 'BNS主机名',
    `bns_sn` VARCHAR(100) COMMENT 'BNS序列号',
    `bns_ip` VARCHAR(50) COMMENT 'BNS IP地址',
    `bns_instancename` VARCHAR(255) COMMENT 'BNS实例名',
    `bns_product` VARCHAR(100) COMMENT 'BNS产品',
    
    -- ========== RMS字段（37个）- 资源管理系统 ==========
    `rms_hostname` VARCHAR(255) COMMENT 'RMS主机名',
    `rms_sn` VARCHAR(100) COMMENT 'RMS序列号',
    `rms_cabinetsn` VARCHAR(100) COMMENT '机柜序列号',
    `rms_server_id` VARCHAR(100) COMMENT '服务器ID',
    `rms_suit` VARCHAR(100) COMMENT '服务器套件',
    `rms_type` VARCHAR(100) COMMENT '服务器类型',
    `rms_status` VARCHAR(50) COMMENT '服务器状态',
    `rms_arrive_time` DATETIME COMMENT '到货时间',
    `rms_online_time` DATETIME COMMENT '上线时间',
    `rms_mod_time` DATETIME COMMENT '修改时间',
    `rms_maintenance_time` DATETIME COMMENT '维保时间',
    `rms_model` VARCHAR(100) COMMENT '服务器型号',
    `rms_rack_info` VARCHAR(100) COMMENT '机架位置',
    `rms_manufacturer` VARCHAR(100) COMMENT '制造商',
    `rms_idc` VARCHAR(100) COMMENT '数据中心',
    `rms_product` VARCHAR(100) COMMENT '产品线',
    `rms_kernel` VARCHAR(100) COMMENT '内核版本',
    `rms_department` VARCHAR(100) COMMENT '所属部门',
    `rms_ilo_ip` VARCHAR(100) COMMENT '带外管理IP',
    `rms_ilo_mac` VARCHAR(100) COMMENT '带外管理MAC',
    `rms_ip_in1` VARCHAR(50) COMMENT '内网IP1',
    `rms_ip_in2` VARCHAR(50) COMMENT '内网IP2',
    `rms_ip_out` VARCHAR(50) COMMENT '外网IP',
    `rms_mac1` VARCHAR(50) COMMENT 'MAC地址1',
    `rms_mac2` VARCHAR(50) COMMENT 'MAC地址2',
    `rms_cpu` TEXT COMMENT 'CPU配置',
    `rms_flash` VARCHAR(255) COMMENT 'Flash存储',
    `rms_harddisk` VARCHAR(255) COMMENT '硬盘配置',
    `rms_memory` TEXT COMMENT '内存配置',
    `rms_networkcard` TEXT COMMENT '网卡配置',
    `rms_raid` VARCHAR(255) COMMENT 'RAID配置',
    `rms_ssd` TEXT COMMENT 'SSD配置',
    `rms_hwfailure_hostname` VARCHAR(255) COMMENT '硬件故障主机名',
    `rms_hwfailure_sn` VARCHAR(100) COMMENT '硬件故障序列号',
    `rms_hwfailure_devices` TEXT COMMENT '故障设备',
    `rms_hwfailure_details` TEXT COMMENT '故障详情',
    `rms_hwfailure_op_type` VARCHAR(50) COMMENT '故障操作类型',
    
    -- ========== Nova Host字段（101个）- OpenStack宿主机 ==========
    `nova_host_hypervisor_id` VARCHAR(100) COMMENT '虚拟化ID',
    `nova_host_hypervisor_hostname` VARCHAR(255) COMMENT '虚拟化主机名',
    `nova_host_cluster` VARCHAR(100) COMMENT '集群名称',
    `nova_host_node_type` VARCHAR(50) COMMENT '节点类型',
    `nova_host_node_state` VARCHAR(50) COMMENT '节点状态',
    `nova_host_azone` VARCHAR(100) COMMENT '可用区',
    `nova_host_group_id` VARCHAR(100) COMMENT '分组ID',
    `nova_host_model` VARCHAR(100) COMMENT '主机型号',
    `nova_host_logical_machine_suit` VARCHAR(100) COMMENT '逻辑机器套件',
    `nova_host_machine_suit` VARCHAR(100) COMMENT '物理机器套件',
    `nova_host_hypervisor_type` VARCHAR(50) COMMENT '虚拟化类型',
    `nova_host_physical_memory_mb_total` BIGINT COMMENT '物理内存总量(MB)',
    `nova_host_physical_memory_mb_free` BIGINT COMMENT '物理内存空闲(MB)',
    `nova_host_physical_disk_gb_free` BIGINT COMMENT '物理磁盘空闲(GB)',
    `nova_host_vcpus_total` INT COMMENT '虚拟CPU总数',
    `nova_host_vcpus_used` INT COMMENT '虚拟CPU已用',
    `nova_host_vcpus_free` INT COMMENT '虚拟CPU空闲',
    `nova_host_running_vms` INT COMMENT '运行中虚拟机数',
    `nova_host_physical_cpus` INT COMMENT '物理CPU数',
    `nova_host_host_ip` VARCHAR(50) COMMENT '主机IP',
    `nova_host_hypervisor_version` VARCHAR(50) COMMENT '虚拟化版本',
    `nova_host_net_bandwidth_kbps` BIGINT COMMENT '网络带宽(Kbps)',
    `nova_host_blacklisted_expired_at` DATETIME COMMENT '黑名单过期时间',
    `nova_host_arrive_time` DATETIME COMMENT '到货时间',
    `nova_host_service_id` VARCHAR(100) COMMENT '服务ID',
    `nova_host_uuid` VARCHAR(100) COMMENT '主机UUID',
    `nova_host_user_id` VARCHAR(100) COMMENT '用户ID',
    `nova_host_cpu_allocation_ratio` VARCHAR(50) COMMENT 'CPU分配比例',
    `nova_host_netbandwidth_allocation_ratio` VARCHAR(50) COMMENT '网络带宽分配比例',
    `nova_host_enable_dpdk` BOOLEAN COMMENT '启用DPDK',
    `nova_host_enable_numa` BOOLEAN COMMENT '启用NUMA',
    `nova_host_enable_turbo` BOOLEAN COMMENT '启用Turbo',
    `nova_host_enable_bind_core` BOOLEAN COMMENT '启用核心绑定',
    `nova_host_tor_ips` TEXT COMMENT 'TOR交换机IP(JSON)',
    `nova_host_has_pci` BOOLEAN COMMENT '是否有PCI设备',
    `nova_host_cds_version` VARCHAR(50) COMMENT 'CDS版本',
    `nova_host_cpuid_md5` VARCHAR(100) COMMENT 'CPU ID MD5',
    `nova_host_qemu_version` VARCHAR(50) COMMENT 'QEMU版本',
    `nova_host_libvirt_version` VARCHAR(50) COMMENT 'Libvirt版本',
    `nova_host_kernel_version` VARCHAR(100) COMMENT '内核版本',
    `nova_host_net_bandwidth` VARCHAR(50) COMMENT '网络带宽',
    `nova_host_disk_bandwidth` VARCHAR(50) COMMENT '磁盘带宽',
    `nova_host_cpu_set` TEXT COMMENT 'CPU集合',
    `nova_host_vcpus_dedicated` INT COMMENT '专用虚拟CPU',
    `nova_host_memory_mb_dedicated` BIGINT COMMENT '专用内存(MB)',
    `nova_host_local_gb_dedicated` BIGINT COMMENT '专用本地存储(GB)',
    `nova_host_project_id` VARCHAR(100) COMMENT '项目ID',
    `nova_host_name` VARCHAR(255) COMMENT '主机名称',
    `nova_host_blacklisted_description` TEXT COMMENT '黑名单描述',
    `nova_host_blacklisted_reason` VARCHAR(255) COMMENT '黑名单原因',
    `nova_host_cpu_info` TEXT COMMENT 'CPU详细信息(JSON)',
    `nova_host_scheduler_label` TEXT COMMENT '调度标签(JSON)',
    `nova_host_disks` TEXT COMMENT '磁盘信息(JSON)',
    `nova_host_pci_devices` TEXT COMMENT 'PCI设备(JSON)',
    `nova_host_sn` VARCHAR(100) COMMENT '序列号',
    `nova_host_memory_mb` BIGINT COMMENT '内存(MB)',
    `nova_host_local_gb` BIGINT COMMENT '本地存储(GB)',
    `nova_host_ilo_ip` VARCHAR(100) COMMENT '带外管理IP',
    `nova_host_bond_mac` VARCHAR(100) COMMENT 'Bond MAC地址',
    `nova_host_interfaces` TEXT COMMENT '网络接口(JSON)',
    `nova_host_tor_if` VARCHAR(100) COMMENT 'TOR接口',
    `nova_host_tor_name` VARCHAR(100) COMMENT 'TOR名称',
    `nova_host_created_at` DATETIME COMMENT '创建时间',
    `nova_host_updated_at` DATETIME COMMENT '更新时间',
    `nova_host_assigned_at` DATETIME COMMENT '分配时间',
    
    -- ========== 系统字段 ==========
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    `synced_at` DATETIME COMMENT '最后同步时间',
    
    -- 索引
    INDEX `idx_bns_hostname` (`bns_hostname`),
    INDEX `idx_rms_sn` (`rms_sn`),
    INDEX `idx_nova_host_azone` (`nova_host_azone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CMDB物理服务器表（完整版）';

-- ============================================
-- CMDB虚拟实例表（完整版 - 175个字段）
-- ============================================
CREATE TABLE `iaas_instances` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    
    -- ========== 关联字段 ==========
    `bns_hostname` VARCHAR(255) COMMENT '所属主机名',
    
    -- ========== Nova VM字段（30+个）- 虚拟机实例 ==========
    `nova_vm_instance_uuid` VARCHAR(100) UNIQUE COMMENT '实例UUID',
    `nova_vm_display_name` VARCHAR(255) COMMENT '显示名称',
    `nova_vm_hypervisor_hostname` VARCHAR(255) COMMENT '宿主机名',
    `nova_vm_cluster` VARCHAR(100) COMMENT '集群',
    `nova_vm_azone` VARCHAR(100) COMMENT '可用区',
    `nova_vm_user_id` VARCHAR(100) COMMENT '用户ID',
    `nova_vm_tenant_id` VARCHAR(255) COMMENT '租户ID（支持多租户ID逗号分隔）',
    `nova_vm_metadata_source` VARCHAR(100) COMMENT '元数据来源',
    `nova_vm_os_type` VARCHAR(50) COMMENT '操作系统类型',
    `nova_vm_flavor_id` VARCHAR(100) COMMENT '规格ID',
    `nova_vm_vcpus` INT COMMENT '虚拟CPU数',
    `nova_vm_memory_mb` INT COMMENT '内存(MB)',
    `nova_vm_root_gb` INT COMMENT '根磁盘(GB)',
    `nova_vm_ephemeral_gb` INT COMMENT '临时磁盘(GB)',
    `nova_vm_hypervisor_dedicated` BOOLEAN COMMENT '专用虚拟化',
    `nova_vm_project_id` VARCHAR(100) COMMENT '项目ID',
    `nova_vm_instance_name` VARCHAR(255) COMMENT '实例名称',
    `nova_vm_image_uuid` VARCHAR(100) COMMENT '镜像UUID',
    `nova_vm_max_net_bandwidth_kbps` BIGINT COMMENT '最大网络带宽(Kbps)',
    `nova_vm_metadata_ephemeral_raw` VARCHAR(50) COMMENT '临时存储元数据',
    `nova_vm_metadata_root_on_cds_v2` VARCHAR(50) COMMENT '根磁盘在CDS V2',
    `nova_vm_metadata_root_on_cds` VARCHAR(50) COMMENT '根磁盘在CDS',
    `nova_vm_metadata_roc_status` VARCHAR(50) COMMENT 'ROC状态',
    `nova_vm_power_state` INT COMMENT '电源状态',
    `nova_vm_root_device_name` VARCHAR(100) COMMENT '根设备名',
    `nova_vm_root_volume_id` VARCHAR(100) COMMENT '根卷ID',
    `nova_vm_task_state` VARCHAR(50) COMMENT '任务状态',
    `nova_vm_vm_state` VARCHAR(50) COMMENT '虚拟机状态',
    `nova_vm_subnets` TEXT COMMENT '子网(JSON)',
    `nova_vm_floating_ips` TEXT COMMENT '浮动IP(JSON)',
    `nova_vm_fixed_ips` TEXT COMMENT '固定IP(JSON)',
    `nova_vm_virtual_disks` TEXT COMMENT '虚拟磁盘(JSON)',
    `nova_vm_volumes_attached` TEXT COMMENT '挂载卷(JSON)',
    `nova_vm_created_at` DATETIME COMMENT '虚拟机创建时间',
    `nova_vm_updated_at` DATETIME COMMENT '虚拟机更新时间',
    `nova_vm_launched_at` DATETIME COMMENT '虚拟机启动时间',
    
    -- ========== Logical字段（15个）- 逻辑实例 ==========
    `logical_instance_id` VARCHAR(100) COMMENT '逻辑实例ID',
    `logical_instance_uuid` VARCHAR(100) COMMENT '逻辑实例UUID',
    `logical_region` VARCHAR(100) COMMENT '逻辑区域',
    `logical_deleted` BOOLEAN COMMENT '是否删除',
    `logical_roc_v2` VARCHAR(50) COMMENT 'ROC V2',
    `logical_user_id` VARCHAR(100) COMMENT '逻辑用户ID',
    `logical_tenant_id` VARCHAR(100) COMMENT '逻辑租户ID',
    `logical_name` VARCHAR(255) COMMENT '逻辑名称',
    `logical_internal_ip` VARCHAR(50) COMMENT '内部IP',
    `logical_floating_ip` VARCHAR(50) COMMENT '浮动IP',
    `logical_status` VARCHAR(50) COMMENT '逻辑状态',
    `logical_order_uuid` VARCHAR(100) COMMENT '订单UUID',
    `logical_dcc_uuid` VARCHAR(100) COMMENT 'DCC UUID',
    `logical_source` VARCHAR(100) COMMENT '来源',
    `logical_application` VARCHAR(100) COMMENT '应用',
    
    -- ========== CRM字段（15个）- 客户关系管理 ==========
    `crm_accountId` VARCHAR(100) COMMENT '账户ID',
    `crm_loginName` VARCHAR(255) COMMENT '登录名',
    `crm_registerTime` DATETIME COMMENT '注册时间',
    `crm_name` VARCHAR(255) COMMENT '账户名称',
    `crm_cname` VARCHAR(255) COMMENT '中文名称',
    `crm_serviceAccount` VARCHAR(100) COMMENT '服务账户',
    `crm_province` VARCHAR(100) COMMENT '省份',
    `crm_city` VARCHAR(100) COMMENT '城市',
    `crm_company` VARCHAR(500) COMMENT '公司名称',
    `crm_vip_type` VARCHAR(50) COMMENT 'VIP类型',
    `crm_industry` VARCHAR(100) COMMENT '行业',
    `crm_industryDetail` VARCHAR(255) COMMENT '行业详情',
    `crm_accountManagers` TEXT COMMENT '客户经理(JSON)',
    `crm_techniqueAccountManagers` TEXT COMMENT '技术客户经理(JSON)',
    `crm_tags` TEXT COMMENT '标签(JSON)',
    
    -- ========== 系统字段 ==========
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    `synced_at` DATETIME COMMENT '最后同步时间',
    
    -- 索引
    INDEX `idx_bns_hostname` (`bns_hostname`),
    INDEX `idx_instance_uuid` (`nova_vm_instance_uuid`),
    INDEX `idx_vm_state` (`nova_vm_vm_state`),
    INDEX `idx_hostname_state` (`bns_hostname`, `nova_vm_vm_state`),
    INDEX `idx_user_id` (`nova_vm_user_id`),
    INDEX `idx_crm_login` (`crm_loginName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CMDB虚拟实例表（完整版）';

SET FOREIGN_KEY_CHECKS = 1;

-- 初始化完成提示
SELECT 'CMDB完整表结构初始化完成！' AS message;
SELECT CONCAT('iaas_servers 表已创建，包含 ', COUNT(*), ' 个字段') AS servers_info 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'iaas_servers';

SELECT CONCAT('iaas_instances 表已创建，包含 ', COUNT(*), ' 个字段') AS instances_info 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'iaas_instances';
