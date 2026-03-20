/**
 * CMDB 字段配置
 * 定义所有可用的服务器和实例字段
 */

// 服务器字段定义（完整的175个字段）
export const serverFieldDefinitions = [
  // ========== 基本信息分组 ==========
  {
    group: '基本信息',
    fields: [
      { key: 'bns_hostname', label: '主机名', minWidth: 180, defaultVisible: true, sortable: false, copyable: true },
      { key: 'rms_sn', label: 'SN', width: 120, minWidth: 100, defaultVisible: true, sortable: false, copyable: true },
      { key: 'rms_manufacturer', label: '品牌', width: 90, minWidth: 80, defaultVisible: true, sortable: false },
      { key: 'rms_type', label: '类型', width: 110, minWidth: 90, defaultVisible: true, sortable: false },
      { key: 'nova_host_node_type', label: '节点类型', width: 100, minWidth: 90, defaultVisible: true, sortable: false },
      { key: 'nova_host_azone', label: '可用区', width: 100, minWidth: 90, defaultVisible: false, sortable: false },
      { key: 'nova_host_cluster', label: '集群', width: 120, minWidth: 100, defaultVisible: false, sortable: false },
      { key: 'rms_model', label: '服务器型号', width: 150, minWidth: 120, defaultVisible: false, sortable: false },
      { key: 'rms_suit', label: '套餐号', width: 120, minWidth: 100, defaultVisible: false, sortable: false },
      { key: 'rms_product', label: '产品线', width: 100, minWidth: 90, defaultVisible: false, sortable: false },
      { key: 'rms_idc', label: '数据中心', width: 120, minWidth: 100, defaultVisible: false, sortable: false },
      { key: 'rms_department', label: '所属部门', width: 120, minWidth: 100, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== 资源使用分组 ==========
  {
    group: '资源使用',
    fields: [
      { key: 'nova_host_vcpus_used', label: 'vCPU', width: 140, defaultVisible: true, sortable: true, type: 'resource', totalKey: 'nova_host_vcpus_total' },
      { key: 'memory_used', label: '内存', width: 160, defaultVisible: true, sortable: true, type: 'resource', totalKey: 'nova_host_physical_memory_mb_total' },
      { key: 'nova_host_running_vms', label: '实例数', width: 100, defaultVisible: true, sortable: true },
      { key: 'nova_host_physical_disk_gb_free', label: '磁盘剩余(GB)', width: 130, defaultVisible: true, sortable: true },
      { key: 'nova_host_vcpus_total', label: 'vCPU总数', width: 100, defaultVisible: false, sortable: false },
      { key: 'nova_host_vcpus_free', label: 'vCPU空闲', width: 100, defaultVisible: false, sortable: false },
      { key: 'nova_host_physical_memory_mb_total', label: '内存总量(MB)', width: 130, defaultVisible: false, sortable: false },
      { key: 'nova_host_physical_memory_mb_free', label: '内存空闲(MB)', width: 130, defaultVisible: false, sortable: false },
      { key: 'nova_host_physical_cpus', label: '物理CPU核数', width: 120, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== 状态信息分组 ==========
  {
    group: '状态信息',
    fields: [
      { key: 'status', label: '状态', minWidth: 80, defaultVisible: true, sortable: false, type: 'status' },
      { key: 'nova_host_node_state', label: '节点状态', width: 100, defaultVisible: false, sortable: false },
      { key: 'nova_host_blacklisted_reason', label: '加黑原因', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_blacklisted_description', label: '加黑说明', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_blacklisted_expired_at', label: '黑名单过期时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
  
  // ========== BNS信息分组 ==========
  {
    group: 'BNS信息',
    fields: [
      { key: 'bns_id', label: 'BNS ID', width: 100, defaultVisible: false, sortable: false },
      { key: 'bns_serviceunit', label: 'BNS服务单元', width: 150, defaultVisible: false, sortable: false },
      { key: 'bns_sn', label: 'BNS序列号', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'bns_ip', label: 'BNS IP', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'bns_instancename', label: 'BNS实例名', width: 150, defaultVisible: false, sortable: false },
      { key: 'bns_product', label: 'BNS产品', width: 120, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== RMS硬件信息分组 ==========
  {
    group: 'RMS硬件信息',
    fields: [
      { key: 'rms_hostname', label: 'RMS主机名', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_cabinetsn', label: '机柜序列号', width: 130, defaultVisible: false, sortable: false },
      { key: 'rms_server_id', label: '服务器ID', width: 120, defaultVisible: false, sortable: false },
      { key: 'rms_status', label: 'RMS状态', width: 100, defaultVisible: false, sortable: false },
      { key: 'rms_rack_info', label: '机架位置', width: 120, defaultVisible: false, sortable: false },
      { key: 'rms_kernel', label: '内核版本', width: 150, defaultVisible: false, sortable: false },
      { key: 'rms_cpu', label: 'CPU配置', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_memory', label: '内存配置', width: 150, defaultVisible: false, sortable: false },
      { key: 'rms_ssd', label: 'SSD配置', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_harddisk', label: '硬盘配置', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_flash', label: 'Flash存储', width: 150, defaultVisible: false, sortable: false },
      { key: 'rms_raid', label: 'RAID配置', width: 150, defaultVisible: false, sortable: false },
      { key: 'rms_networkcard', label: '网卡配置', width: 200, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== RMS网络信息分组 ==========
  {
    group: 'RMS网络信息',
    fields: [
      { key: 'rms_ilo_ip', label: '带外管理IP', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_ilo_mac', label: '带外管理MAC', width: 150, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_ip_in1', label: '内网IP1', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_ip_in2', label: '内网IP2', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_ip_out', label: '外网IP', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_mac1', label: 'MAC地址1', width: 150, defaultVisible: false, sortable: false, copyable: true },
      { key: 'rms_mac2', label: 'MAC地址2', width: 150, defaultVisible: false, sortable: false, copyable: true },
    ]
  },
  
  // ========== RMS时间信息分组 ==========
  {
    group: 'RMS时间信息',
    fields: [
      { key: 'rms_arrive_time', label: 'RMS到货时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'rms_online_time', label: 'RMS上线时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'rms_mod_time', label: 'RMS修改时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'rms_maintenance_time', label: 'RMS维保时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
  
  // ========== RMS故障信息分组 ==========
  {
    group: 'RMS故障信息',
    fields: [
      { key: 'rms_hwfailure_hostname', label: '故障主机名', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_hwfailure_sn', label: '故障序列号', width: 130, defaultVisible: false, sortable: false },
      { key: 'rms_hwfailure_devices', label: '故障设备', width: 200, defaultVisible: false, sortable: false },
      { key: 'rms_hwfailure_details', label: '故障详情', width: 250, defaultVisible: false, sortable: false },
      { key: 'rms_hwfailure_op_type', label: '故障操作类型', width: 120, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== Nova虚拟化信息分组 ==========
  {
    group: 'Nova虚拟化信息',
    fields: [
      { key: 'nova_host_hypervisor_id', label: '虚拟化ID', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_hypervisor_hostname', label: '虚拟化主机名', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_hypervisor_type', label: '虚拟化类型', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_hypervisor_version', label: '虚拟化版本', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_group_id', label: '分组ID', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_model', label: 'Nova主机型号', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_logical_machine_suit', label: '逻辑机器套件', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_machine_suit', label: '物理机器套件', width: 150, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== Nova网络信息分组 ==========
  {
    group: 'Nova网络信息',
    fields: [
      { key: 'nova_host_host_ip', label: 'Nova主机IP', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_host_ilo_ip', label: 'Nova带外IP', width: 130, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_host_bond_mac', label: 'Bond MAC', width: 150, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_host_net_bandwidth_kbps', label: '网络带宽(Kbps)', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_net_bandwidth', label: '网络带宽', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_tor_if', label: 'TOR接口', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_tor_name', label: 'TOR名称', width: 120, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== Nova配置信息分组 ==========
  {
    group: 'Nova配置信息',
    fields: [
      { key: 'nova_host_cpu_allocation_ratio', label: 'CPU分配比例', width: 130, defaultVisible: false, sortable: false },
      { key: 'nova_host_netbandwidth_allocation_ratio', label: '带宽分配比例', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_enable_dpdk', label: '启用DPDK', width: 100, defaultVisible: false, sortable: false, type: 'boolean' },
      { key: 'nova_host_enable_numa', label: '启用NUMA', width: 100, defaultVisible: false, sortable: false, type: 'boolean' },
      { key: 'nova_host_enable_turbo', label: '启用Turbo', width: 100, defaultVisible: false, sortable: false, type: 'boolean' },
      { key: 'nova_host_enable_bind_core', label: '启用核心绑定', width: 120, defaultVisible: false, sortable: false, type: 'boolean' },
      { key: 'nova_host_has_pci', label: '有PCI设备', width: 100, defaultVisible: false, sortable: false, type: 'boolean' },
    ]
  },
  
  // ========== Nova版本信息分组 ==========
  {
    group: 'Nova版本信息',
    fields: [
      { key: 'nova_host_cds_version', label: 'CDS版本', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_qemu_version', label: 'QEMU版本', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_libvirt_version', label: 'Libvirt版本', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_kernel_version', label: 'Nova内核版本', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_cpuid_md5', label: 'CPU ID MD5', width: 200, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== Nova存储信息分组 ==========
  {
    group: 'Nova存储信息',
    fields: [
      { key: 'nova_host_memory_mb', label: 'Nova内存(MB)', width: 130, defaultVisible: false, sortable: false },
      { key: 'nova_host_local_gb', label: 'Nova本地存储(GB)', width: 150, defaultVisible: false, sortable: false },
      { key: 'nova_host_disk_bandwidth', label: '磁盘带宽', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_host_vcpus_dedicated', label: '专用vCPU', width: 100, defaultVisible: false, sortable: false },
      { key: 'nova_host_memory_mb_dedicated', label: '专用内存(MB)', width: 130, defaultVisible: false, sortable: false },
      { key: 'nova_host_local_gb_dedicated', label: '专用存储(GB)', width: 130, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== Nova标识信息分组 ==========
  {
    group: 'Nova标识信息',
    fields: [
      { key: 'nova_host_service_id', label: '服务ID', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_uuid', label: 'Nova UUID', width: 250, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_host_user_id', label: '用户ID', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_project_id', label: '项目ID', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_name', label: 'Nova名称', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_host_sn', label: 'Nova序列号', width: 130, defaultVisible: false, sortable: false, copyable: true },
    ]
  },
  
  // ========== Nova时间信息分组 ==========
  {
    group: 'Nova时间信息',
    fields: [
      { key: 'nova_host_arrive_time', label: 'Nova到货时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_host_created_at', label: 'Nova创建时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_host_updated_at', label: 'Nova更新时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_host_assigned_at', label: 'Nova分配时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
  
  // ========== 系统信息分组 ==========
  {
    group: '系统信息',
    fields: [
      { key: 'created_at', label: '记录创建时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'updated_at', label: '记录更新时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'synced_at', label: '最后同步时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
]

// 实例字段定义
export const instanceFieldDefinitions = [
  // ========== 基本信息分组 ==========
  {
    group: '基本信息',
    fields: [
      { key: 'nova_vm_instance_uuid', label: '实例UUID', minWidth: 220, defaultVisible: true, sortable: false, copyable: true },
      { key: 'bns_hostname', label: '所属主机', minWidth: 180, defaultVisible: true, sortable: false, copyable: true },
      { key: 'nova_vm_fixed_ips', label: 'IP地址', width: 150, defaultVisible: true, sortable: false, copyable: true },
      { key: 'nova_vm_metadata_source', label: '实例类型', width: 100, defaultVisible: true, sortable: false },
      { key: 'nova_vm_display_name', label: '显示名称', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_vm_hypervisor_hostname', label: '宿主机名', width: 200, defaultVisible: false, sortable: false },
      { key: 'nova_vm_cluster', label: '集群', width: 120, defaultVisible: false, sortable: false },
      { key: 'nova_vm_azone', label: '可用区', width: 100, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== 资源配置分组 ==========
  {
    group: '资源配置',
    fields: [
      { key: 'nova_vm_vcpus', label: 'vCPU', width: 80, defaultVisible: true, sortable: false },
      { key: 'nova_vm_memory_mb', label: '内存', width: 100, defaultVisible: true, sortable: false, type: 'memory' },
      { key: 'nova_vm_root_gb', label: '系统盘(GB)', width: 100, defaultVisible: true, sortable: false },
      { key: 'nova_vm_ephemeral_gb', label: '临时盘(GB)', width: 100, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== 状态信息分组 ==========
  {
    group: '状态信息',
    fields: [
      { key: 'nova_vm_vm_state', label: '状态', minWidth: 90, defaultVisible: true, sortable: false, type: 'status' },
      { key: 'nova_vm_power_state', label: '电源状态', width: 100, defaultVisible: false, sortable: false },
      { key: 'nova_vm_task_state', label: '任务状态', width: 100, defaultVisible: false, sortable: false },
    ]
  },
  
  // ========== 标识信息分组 ==========
  {
    group: '标识信息',
    fields: [
      { key: 'nova_vm_project_id', label: '项目ID', width: 250, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_vm_user_id', label: '用户ID', width: 250, defaultVisible: false, sortable: false, copyable: true },
      { key: 'nova_vm_tenant_id', label: '租户ID', width: 250, defaultVisible: false, sortable: false, copyable: true },
    ]
  },
  
  // ========== 时间信息分组 ==========
  {
    group: '时间信息',
    fields: [
      { key: 'nova_vm_created_at', label: '创建时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_vm_updated_at', label: '更新时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_vm_launched_at', label: '启动时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'nova_vm_terminated_at', label: '终止时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
  
  // ========== 系统信息分组 ==========
  {
    group: '系统信息',
    fields: [
      { key: 'created_at', label: '记录创建时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'updated_at', label: '记录更新时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
      { key: 'synced_at', label: '最后同步时间', width: 160, defaultVisible: false, sortable: false, type: 'datetime' },
    ]
  },
]

// 获取默认可见字段
export function getDefaultVisibleFields(viewMode) {
  const definitions = viewMode === 'servers' ? serverFieldDefinitions : instanceFieldDefinitions
  const visibleFields = []
  
  definitions.forEach(group => {
    group.fields.forEach(field => {
      if (field.defaultVisible) {
        visibleFields.push(field.key)
      }
    })
  })
  
  return visibleFields
}

// 获取所有字段（扁平化）
export function getAllFields(viewMode) {
  const definitions = viewMode === 'servers' ? serverFieldDefinitions : instanceFieldDefinitions
  const allFields = []
  
  definitions.forEach(group => {
    group.fields.forEach(field => {
      allFields.push({
        ...field,
        group: group.group
      })
    })
  })
  
  return allFields
}

// 根据key获取字段配置
export function getFieldConfig(viewMode, key) {
  const allFields = getAllFields(viewMode)
  return allFields.find(f => f.key === key)
}
