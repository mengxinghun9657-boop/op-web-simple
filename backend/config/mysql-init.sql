-- ============================================
-- 集群管理平台 - MySQL 数据库初始化脚本
-- ============================================

-- 设置字符集
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 用户表（SQLite 迁移到 MySQL）
-- ============================================
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `email` VARCHAR(100) DEFAULT NULL,
    `hashed_password` VARCHAR(255) NOT NULL,
    `full_name` VARCHAR(100) DEFAULT NULL,
    `role` ENUM('super_admin', 'admin', 'analyst', 'viewer') NOT NULL DEFAULT 'viewer',
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `last_login` DATETIME DEFAULT NULL,
    INDEX `idx_username` (`username`),
    INDEX `idx_email` (`email`),
    INDEX `idx_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 审计日志表
-- ============================================
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT DEFAULT NULL,
    `username` VARCHAR(50) NOT NULL,
    `action` VARCHAR(50) NOT NULL,
    `resource` VARCHAR(100) DEFAULT NULL,
    `ip_address` VARCHAR(50) DEFAULT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_username` (`username`),
    INDEX `idx_action` (`action`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';

-- ============================================
-- 任务表
-- ============================================
CREATE TABLE IF NOT EXISTS `tasks` (
    `id` VARCHAR(50) PRIMARY KEY COMMENT '任务ID',
    `task_type` VARCHAR(50) NOT NULL DEFAULT 'prometheus_batch' COMMENT '任务类型',
    `user_id` INT DEFAULT NULL,
    `status` VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    `progress` INT DEFAULT 0 COMMENT '进度百分比',
    `total_items` INT DEFAULT 0 COMMENT '总项目数',
    `completed_items` INT DEFAULT 0 COMMENT '已完成项目数',
    `message` VARCHAR(500) DEFAULT NULL COMMENT '任务消息',
    `file_name` VARCHAR(255) DEFAULT NULL COMMENT '原始文件名',
    `file_path` VARCHAR(500) DEFAULT NULL COMMENT '上传文件路径',
    `result_path` VARCHAR(500) DEFAULT NULL COMMENT '结果文件路径',
    `result_url` VARCHAR(500) DEFAULT NULL COMMENT '结果文件URL',
    `username` VARCHAR(100) DEFAULT NULL COMMENT '创建用户名',
    `error_message` TEXT COMMENT '错误信息',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `completed_at` DATETIME DEFAULT NULL,
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_task_type` (`task_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`),
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务表';

-- ============================================
-- GPU HAS 自动化巡检记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `gpu_inspection_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `instance_id` VARCHAR(100) NOT NULL UNIQUE COMMENT '实例ID',
    `instance_name` VARCHAR(255) NOT NULL COMMENT '实例名称',
    `gpu_card` VARCHAR(50) NOT NULL COMMENT 'GPU型号',
    `internal_ip` VARCHAR(64) DEFAULT NULL COMMENT '内网IP',
    `has_alive` VARCHAR(32) NOT NULL DEFAULT 'unknown' COMMENT 'HAS状态',
    `region` VARCHAR(50) DEFAULT NULL COMMENT '区域',
    `source_updated_at` DATETIME DEFAULT NULL COMMENT '源数据更新时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_instance_name` (`instance_name`),
    INDEX `idx_internal_ip` (`internal_ip`),
    INDEX `idx_gpu_card` (`gpu_card`),
    INDEX `idx_has_alive` (`has_alive`),
    INDEX `idx_region` (`region`),
    INDEX `idx_status_card` (`has_alive`, `gpu_card`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GPU HAS自动化巡检记录表';

-- ============================================
-- APIServer 监控告警记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `apiserver_alert_records` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `fingerprint` VARCHAR(255) NOT NULL UNIQUE COMMENT '告警指纹',
    `cluster_id` VARCHAR(200) NOT NULL COMMENT '集群ID',
    `metric_key` VARCHAR(100) NOT NULL COMMENT '指标键',
    `metric_label` VARCHAR(200) NOT NULL COMMENT '指标名称',
    `severity` VARCHAR(50) NOT NULL DEFAULT 'warning' COMMENT '严重程度',
    `status` VARCHAR(50) NOT NULL DEFAULT 'active' COMMENT '状态',
    `current_value` DOUBLE NOT NULL DEFAULT 0 COMMENT '当前值',
    `warning_threshold` DOUBLE DEFAULT NULL COMMENT '警告阈值',
    `critical_threshold` DOUBLE DEFAULT NULL COMMENT '严重阈值',
    `unit` VARCHAR(50) DEFAULT NULL COMMENT '单位',
    `window_minutes` VARCHAR(50) DEFAULT NULL COMMENT '统计窗口',
    `promql` TEXT COMMENT 'PromQL',
    `description` TEXT COMMENT '影响描述',
    `suggestion` TEXT COMMENT '建议动作',
    `labels` JSON DEFAULT NULL COMMENT '附加标签',
    `source` VARCHAR(50) NOT NULL DEFAULT 'prometheus' COMMENT '来源',
    `notified` VARCHAR(10) NOT NULL DEFAULT 'false' COMMENT '是否已通知',
    `notified_at` DATETIME DEFAULT NULL COMMENT '通知时间',
    `last_seen_at` DATETIME DEFAULT NULL COMMENT '最近检测时间',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `resolved_at` DATETIME DEFAULT NULL COMMENT '恢复时间',
    `resolved_by` VARCHAR(100) DEFAULT NULL COMMENT '处理人',
    `resolution_notes` TEXT DEFAULT NULL COMMENT '处理备注',
    `resolution_result` VARCHAR(50) DEFAULT NULL COMMENT '处理结果',
    `icafe_card_id` VARCHAR(100) DEFAULT NULL COMMENT '关联 iCafe 卡片ID',
    INDEX `idx_apiserver_cluster_status` (`cluster_id`, `status`),
    INDEX `idx_apiserver_metric_status` (`metric_key`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='APIServer 监控告警记录表';

-- ============================================
-- CMDB物理服务器表（完整版 - 145个字段）
-- ============================================
CREATE TABLE IF NOT EXISTS `iaas_servers` (
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
-- CMDB虚拟实例表（完整版 - 80个字段）
-- ============================================
CREATE TABLE IF NOT EXISTS `iaas_instances` (
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

-- ============================================
-- 插入默认超级管理员账号
-- ============================================
-- 密码: admin123 (请在首次登录后立即修改)
-- 使用 bcrypt 加密，可通过以下 Python 代码生成:
-- from passlib.context import CryptContext
-- pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
-- print(pwd_context.hash("admin123"))

INSERT INTO `users` (`username`, `email`, `hashed_password`, `full_name`, `role`, `is_active`)
VALUES
    ('admin', 'admin@cluster.local', '$2b$12$wVcucYK8bP/2iRybdeDkpef.oXI2cR9XvH/fgWMEaLLkGGk3dX/HC', '系统管理员', 'super_admin', TRUE)
ON DUPLICATE KEY UPDATE
    `email` = VALUES(`email`),
    `full_name` = VALUES(`full_name`);

-- ============================================
-- 插入测试数据（开发环境）
-- ============================================
-- 分析师账号: analyst / analyst123
INSERT INTO `users` (`username`, `email`, `hashed_password`, `full_name`, `role`, `is_active`)
VALUES
    ('analyst', 'analyst@cluster.local', '$2b$12$b7zszdauQIcNsxTPpT7cFenH82Aokasyr69rjpNFUuHp/nyDliZOm', '数据分析师', 'analyst', TRUE)
ON DUPLICATE KEY UPDATE
    `email` = VALUES(`email`),
    `full_name` = VALUES(`full_name`);

-- 查看者账号: viewer / viewer123
INSERT INTO `users` (`username`, `email`, `hashed_password`, `full_name`, `role`, `is_active`)
VALUES
    ('viewer', 'viewer@cluster.local', '$2b$12$0ikJY0FpxmivcAWcsgb.GuzqGfOklmlaW138Byrsp18nccZLqpuJK', '查看用户', 'viewer', TRUE)
ON DUPLICATE KEY UPDATE
    `email` = VALUES(`email`),
    `full_name` = VALUES(`full_name`);

-- ============================================
-- 查看表结构
-- ============================================
SHOW TABLES;

SET FOREIGN_KEY_CHECKS = 1;

-- 初始化完成提示
SELECT '数据库初始化完成！' AS message;
SELECT CONCAT('默认管理员账号: admin / admin123 (请立即修改密码)') AS notice;


-- ============================================
-- 硬件告警诊断系统 - 数据库表初始化脚本
-- ============================================

-- ============================================
-- 告警记录表
-- ============================================
CREATE TABLE IF NOT EXISTS `alert_records` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `alert_type` VARCHAR(200) NOT NULL COMMENT '告警类型',
    
    -- 位置信息（用于分组统计）
    `ip` VARCHAR(100) COMMENT '节点IP地址',
    `cluster_id` VARCHAR(200) COMMENT '集群ID（CCE集群专用）',
    `instance_id` VARCHAR(200) COMMENT '实例ID（物理机专用）',
    `hostname` VARCHAR(200) COMMENT '主机名/节点名',
    
    -- 告警属性（用于筛选和统计）
    `component` VARCHAR(100) COMMENT '组件类型(GPU/Memory/CPU/Motherboard等)',
    `severity` VARCHAR(50) NOT NULL COMMENT '严重程度(critical/warning/info等)',
    
    -- 时间信息（用于时间趋势分析）
    `timestamp` DATETIME NOT NULL COMMENT '告警发生时间',
    
    -- 文件信息
    `file_path` VARCHAR(1000) COMMENT '源文件路径',
    
    -- 告警来源
    `source` VARCHAR(50) DEFAULT 'file' COMMENT '告警来源(file/manual)',  -- file: 文件解析, manual: 手动录入
    
    -- 原始数据（完整保存，支持未来重新解析）
    `raw_data` JSON COMMENT '告警原始数据（完整JSON）',
    
    -- 处理状态
    `status` VARCHAR(50) DEFAULT 'pending' COMMENT '处理状态(pending/processing/diagnosed/notified/failed/resolved)',
    
    -- 处理信息
    `resolved_by` VARCHAR(100) COMMENT '处理人',
    `resolved_at` DATETIME COMMENT '处理时间',
    `resolution_notes` TEXT COMMENT '处理备注',
    `resolution_result` TEXT COMMENT '处理结果（告警处理完毕后填写）',

    -- 是否CCE集群（用于区分处理流程）
    `is_cce_cluster` BOOLEAN DEFAULT FALSE COMMENT '是否CCE集群告警',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 索引
    INDEX `idx_alert_type` (`alert_type`),
    INDEX `idx_ip` (`ip`),
    INDEX `idx_cluster_id` (`cluster_id`),
    INDEX `idx_component` (`component`),
    INDEX `idx_severity` (`severity`),
    INDEX `idx_timestamp` (`timestamp`),
    INDEX `idx_status` (`status`),
    INDEX `idx_source` (`source`),
    INDEX `idx_is_cce_cluster` (`is_cce_cluster`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_timestamp_severity` (`timestamp`, `severity`),
    INDEX `idx_cluster_timestamp` (`cluster_id`, `timestamp`),
    INDEX `idx_component_timestamp` (`component`, `timestamp`),
    INDEX `idx_status_timestamp` (`status`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='硬件告警记录表';

-- ============================================
-- 诊断结果表
-- ============================================
CREATE TABLE IF NOT EXISTS `diagnosis_results` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `alert_id` BIGINT NOT NULL UNIQUE COMMENT '关联告警ID（一对一）',
    
    -- 诊断来源
    `source` VARCHAR(50) NOT NULL COMMENT '诊断来源(manual/api/manual+api)',
    
    -- ========== 手册匹配结果 ==========
    `manual_matched` BOOLEAN DEFAULT FALSE COMMENT '是否匹配到手册',
    `manual_name_zh` VARCHAR(500) COMMENT '故障中文名称',
    `manual_solution` TEXT COMMENT '手册解决方案（完整文本）',
    `manual_impact` TEXT COMMENT '影响描述',
    `manual_recovery` TEXT COMMENT '恢复方案',
    `danger_level` VARCHAR(50) COMMENT '危害等级（严重/中等/轻微）',
    `customer_aware` BOOLEAN COMMENT '是否客户有感',
    
    -- 多故障类型详情（JSON格式，用于前端表格展示）
    `fault_items` JSON COMMENT '故障类型列表（包含设备、故障名、解决方案等）',
    
    -- ========== API诊断结果（仅CCE集群） ==========
    `api_task_id` VARCHAR(200) COMMENT 'API任务ID',
    `api_status` VARCHAR(50) COMMENT 'API任务状态(normal/abnormal/failed)',
    
    -- API诊断统计字段（用于快速查询）
    `api_items_count` INT DEFAULT 0 COMMENT '诊断项总数',
    `api_error_count` INT DEFAULT 0 COMMENT '错误项数量',
    `api_warning_count` INT DEFAULT 0 COMMENT '警告项数量',
    `api_abnormal_count` INT DEFAULT 0 COMMENT '异常项数量',
    
    -- API诊断完整报告（JSON格式，包含所有诊断项）
    `api_diagnosis` JSON COMMENT 'API诊断完整报告（包含raw_report）',
    
    -- ========== AI解读结果 ==========
    `ai_interpretation` TEXT COMMENT 'AI解读完整内容（Markdown）',
    
    -- AI解读提取字段（用于快速展示）
    `ai_category` VARCHAR(100) COMMENT 'AI问题分类',
    `ai_root_cause` TEXT COMMENT '根本原因分析',
    `ai_impact` TEXT COMMENT '影响评估',
    `ai_solution` TEXT COMMENT '修复建议',
    
    -- ========== 通知状态 ==========
    `notified` BOOLEAN DEFAULT FALSE COMMENT '是否已发送通知',
    `notified_at` DATETIME COMMENT '通知发送时间',
    
    -- 时间戳
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_source` (`source`),
    INDEX `idx_manual_matched` (`manual_matched`),
    INDEX `idx_danger_level` (`danger_level`),
    INDEX `idx_api_status` (`api_status`),
    
    -- 外键
    FOREIGN KEY (`alert_id`) REFERENCES `alert_records`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='诊断结果表';

-- ============================================
-- Webhook配置表
-- ============================================
-- Webhook配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `webhook_configs` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `name` VARCHAR(200) NOT NULL COMMENT '配置名称',
    `type` VARCHAR(50) NOT NULL COMMENT 'Webhook类型(feishu/ruliu)',
    `url` VARCHAR(1000) NOT NULL COMMENT 'Webhook URL',
    `access_token` VARCHAR(500) COMMENT '访问令牌',
    `secret` VARCHAR(500) COMMENT '签名密钥（飞书专用）',
    `group_id` VARCHAR(200) COMMENT '群组ID（如流专用）',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    
    -- 触发条件（JSON格式，支持复杂过滤规则）
    `severity_filter` VARCHAR(200) COMMENT '严重程度过滤(critical,warning)',
    `component_filter` VARCHAR(500) COMMENT '组件过滤(GPU,Memory)',
    `keywords` VARCHAR(200) COMMENT '飞书机器人关键词(如: 告警，仅飞书需要)',
    
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_type` (`type`),
    INDEX `idx_enabled` (`enabled`),
    INDEX `idx_type_enabled` (`type`, `enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Webhook配置表';

-- ============================================
-- 故障手册表
-- ============================================
CREATE TABLE IF NOT EXISTS `fault_manual` (
    `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `category` VARCHAR(100) NOT NULL COMMENT '类别(GPU/CPU/Memory等)',
    `alert_type` VARCHAR(200) NOT NULL COMMENT '告警类型',
    `has_level` VARCHAR(50) COMMENT 'HAS级别',
    `name_zh` VARCHAR(500) COMMENT '中文名称',
    `impact` TEXT COMMENT '影响描述',
    `recovery_plan` TEXT COMMENT '恢复方案',
    `danger_level` VARCHAR(50) COMMENT '危害等级',
    `customer_aware` BOOLEAN COMMENT '是否客户有感',
    `manual_check` TEXT COMMENT '手动判断方法',
    
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX `idx_category` (`category`),
    INDEX `idx_alert_type` (`alert_type`),
    UNIQUE INDEX `uk_category_type` (`category`, `alert_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='故障手册表';

-- ============================================
-- 监控路径配置表
-- ============================================
-- 硬件告警诊断系统初始化完成
SELECT '硬件告警诊断系统数据库表初始化完成！' AS hardware_alert_message;

-- ============================================
-- CMDB配置管理 - 数据库表初始化脚本
-- ============================================

-- ============================================
-- CMDB配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `cmdb_config` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `config_key` VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    `config_value` TEXT COMMENT '配置值',
    `config_type` VARCHAR(50) DEFAULT 'string' COMMENT '配置类型: string, json, encrypted',
    `description` VARCHAR(500) COMMENT '配置说明',
    `is_active` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `updated_by` VARCHAR(100) COMMENT '更新人',
    
    INDEX `idx_config_key` (`config_key`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CMDB配置表';

-- ============================================
-- CMDB同步日志表
-- ============================================
CREATE TABLE IF NOT EXISTS `cmdb_sync_log` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `sync_type` VARCHAR(50) COMMENT '同步类型: api, excel',
    `azone` VARCHAR(100) COMMENT '可用区',
    `status` VARCHAR(50) COMMENT '状态: success, failed, running',
    `total_rows` INT DEFAULT 0 COMMENT '总记录数',
    `servers_added` INT DEFAULT 0 COMMENT '新增服务器数',
    `servers_updated` INT DEFAULT 0 COMMENT '更新服务器数',
    `instances_added` INT DEFAULT 0 COMMENT '新增实例数',
    `instances_updated` INT DEFAULT 0 COMMENT '更新实例数',
    `error_message` TEXT COMMENT '错误信息',
    `started_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    `completed_at` DATETIME COMMENT '完成时间',
    `duration_seconds` INT COMMENT '耗时（秒）',
    `triggered_by` VARCHAR(100) COMMENT '触发人',
    
    INDEX `idx_sync_type` (`sync_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='CMDB同步日志表';

-- CMDB配置管理初始化完成
SELECT 'CMDB配置管理数据库表初始化完成！' AS cmdb_config_message;

-- ============================================
-- 系统配置管理 - 数据库表初始化脚本
-- ============================================

-- ============================================
-- 系统配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `system_config` (
    `id` INT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    `module` VARCHAR(50) NOT NULL COMMENT '模块名称: cmdb, monitoring, analysis',
    `config_key` VARCHAR(100) NOT NULL COMMENT '配置键',
    `config_value` TEXT COMMENT '配置值（JSON格式）',
    `description` VARCHAR(500) COMMENT '配置说明',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL COMMENT '更新时间',
    `updated_by` INT COMMENT '更新人ID',
    
    INDEX `idx_module` (`module`),
    INDEX `idx_config_key` (`config_key`),
    UNIQUE INDEX `uq_module_config_key` (`module`, `config_key`),
    FOREIGN KEY (`updated_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 系统配置管理初始化完成
SELECT '系统配置管理数据库表初始化完成！' AS system_config_message;

-- ============================================
-- 用户权限配置
-- ============================================

-- 授予 cluster_user 用户对 cluster_management 数据库的所有权限
-- 注意：这里使用环境变量 ${MYSQL_USER} 和 ${MYSQL_PASSWORD}
-- 但由于 SQL 中无法直接使用环境变量，所以使用通配符 'cluster_user'@'%'
-- MySQL 官方镜像会根据 MYSQL_USER 和 MYSQL_PASSWORD 环境变量创建用户

-- 首先检查用户是否存在，如果不存在则创建
-- 注意：这里假设用户名为 cluster_user（根据 docker-compose 中的 MYSQL_USER 配置）
CREATE USER IF NOT EXISTS 'cluster_user'@'%' IDENTIFIED BY 'ClusterPass2024!';

-- 授予所有权限
GRANT ALL PRIVILEGES ON cluster_management.* TO 'cluster_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证权限
SELECT '✅ 用户权限配置完成！' AS permission_message;
SELECT '用户: cluster_user' AS user_info;
SELECT '权限: 所有权限 (ALL PRIVILEGES)' AS privileges_info;
SELECT '数据库: cluster_management' AS database_info;


-- ============================================

-- ============================================
-- 文件监控路径配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `monitor_paths` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '路径ID',
    `path` VARCHAR(500) NOT NULL COMMENT '监控路径',
    `description` VARCHAR(500) COMMENT '路径描述',
    `enabled` BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    `priority` INT DEFAULT 50 COMMENT '优先级(1-100)',
    `file_pattern` VARCHAR(200) DEFAULT '*.txt' COMMENT '文件匹配模式',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY `uk_path` (`path`),
    INDEX `idx_monitor_paths_enabled` (`enabled`),
    INDEX `idx_monitor_paths_priority` (`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文件监控路径配置表';

-- 插入默认监控路径
INSERT INTO `monitor_paths` (`path`, `description`, `enabled`, `priority`, `file_pattern`) 
VALUES ('/data/HAS_file/changan', '长安告警文件目录', TRUE, 100, '*.txt')
ON DUPLICATE KEY UPDATE `enabled`=`enabled`;

SELECT '✅ 文件监控路径配置表初始化完成！' AS monitor_paths_message;

-- ============================================
-- ============================================
-- AI 对话历史表
-- ============================================
CREATE TABLE IF NOT EXISTS `chat_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL COMMENT '用户ID',
    `role` VARCHAR(20) NOT NULL COMMENT 'user/assistant/system',
    `content` TEXT NOT NULL COMMENT '消息内容',
    `context_data` TEXT NULL COMMENT 'JSON格式上下文数据',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_chat_history_user_id` (`user_id`),
    INDEX `idx_chat_history_created_at` (`created_at`),
    CONSTRAINT `fk_chat_history_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI对话历史';

-- ============================================
-- 用户备忘表
-- ============================================
CREATE TABLE IF NOT EXISTS `user_notes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE COMMENT '用户ID',
    `content` TEXT COMMENT '备忘内容',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    CONSTRAINT `fk_user_notes_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户备忘';

-- ============================================
-- 实例配置表
-- ============================================
CREATE TABLE IF NOT EXISTS `instance_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `config_type` VARCHAR(50) NOT NULL UNIQUE COMMENT '配置类型',
    `instance_ids` TEXT NOT NULL COMMENT '实例ID列表（JSON数组格式）',
    `description` VARCHAR(500) NULL COMMENT '配置说明',
    `created_by` VARCHAR(100) NULL COMMENT '创建者',
    `updated_by` VARCHAR(100) NULL COMMENT '更新者',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实例配置表';

SELECT '✅ 新增表初始化完成！(chat_history, user_notes, instance_config)' AS new_tables_message;
