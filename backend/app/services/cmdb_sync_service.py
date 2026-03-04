#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDB同步服务
支持从AMIS API同步数据
"""
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from app.models.iaas import IaasServer, IaasInstance
from app.models.cmdb_config import CMDBConfig, CMDBSyncLog


class CMDBSyncService:
    """CMDB同步服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_url = "https://amis.baidu.com/api/function/iaasops/hypervisor_vm_cross"
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        config = self.db.query(CMDBConfig).filter(
            CMDBConfig.config_key == key,
            CMDBConfig.is_active == True
        ).first()
        
        if not config:
            return default
        
        # 根据类型解析值
        if config.config_type == "json":
            try:
                return json.loads(config.config_value)
            except:
                return default
        elif config.config_type == "int":
            try:
                return int(config.config_value)
            except:
                return default
        elif config.config_type == "bool":
            return config.config_value.lower() in ["true", "1", "yes"]
        else:
            return config.config_value
    
    def set_config(self, key: str, value: Any, config_type: str = "string", 
                   description: str = "", updated_by: str = "system"):
        """设置配置"""
        config = self.db.query(CMDBConfig).filter(
            CMDBConfig.config_key == key
        ).first()
        
        # 转换值为字符串
        if config_type == "json":
            value_str = json.dumps(value, ensure_ascii=False)
        else:
            value_str = str(value)
        
        if config:
            config.config_value = value_str
            config.config_type = config_type
            config.description = description
            config.updated_by = updated_by
            config.updated_at = datetime.utcnow()
        else:
            config = CMDBConfig(
                config_key=key,
                config_value=value_str,
                config_type=config_type,
                description=description,
                updated_by=updated_by
            )
            self.db.add(config)
        
        self.db.commit()
        return config
    
    def get_cookie(self) -> Optional[str]:
        """获取AMIS Cookie"""
        # 优先从 system_config 表读取（新的统一配置方式）
        try:
            from app.models.system_config import SystemConfig
            config_record = self.db.query(SystemConfig).filter(
                SystemConfig.module == 'cmdb',
                SystemConfig.config_key == 'main'
            ).first()
            
            if config_record and config_record.config_value:
                import json
                config = json.loads(config_record.config_value)
                cookie = config.get('api_cookie')
                if cookie:
                    return cookie
        except Exception as e:
            logger.warning(f"从 system_config 读取 Cookie 失败: {e}")
        
        # 兼容旧的 cmdb_config 表
        cookie = self.get_config("amis_cookie")
        if not cookie:
            logger.warning("AMIS Cookie未配置")
        return cookie
    
    def test_cookie(self, cookie: str) -> bool:
        """测试Cookie是否有效"""
        try:
            headers = {
                "Cookie": cookie,
                "Referer": "https://amis.baidu.com/group/iaasops/bcc/hypervisor_vm_cross",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            response = requests.get(
                self.api_url,
                params={"page": 1, "perPage": 1, "nova_host_azone": "AZONE-cdhmlcc001"},
                headers=headers,
                timeout=10
            )
            
            # 检查响应状态码
            if response.status_code != 200:
                logger.error(f"API返回错误状态码: {response.status_code}")
                return False
            
            # 检查响应内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                logger.error(f"API返回非JSON响应，Content-Type: {content_type}")
                logger.error(f"响应内容前200字符: {response.text[:200]}")
                return False
            
            # 尝试解析JSON
            try:
                data = response.json()
            except ValueError as json_err:
                logger.error(f"JSON解析失败: {json_err}")
                logger.error(f"响应内容前200字符: {response.text[:200]}")
                return False
            
            # 检查API返回的状态
            if data.get("status") == 0:
                # 进一步检查是否有数据返回（确认真的认证成功）
                if "data" in data:
                    logger.info("Cookie测试成功，API认证有效")
                    return True
                else:
                    logger.warning("API返回status=0但无data字段，可能认证失败")
                    return False
            else:
                error_msg = data.get('message', data.get('msg', 'N/A'))
                logger.error(f"API返回错误状态: {data.get('status')}, 消息: {error_msg}")
                # 检查是否是认证相关错误
                if any(keyword in str(error_msg).lower() for keyword in ['login', 'auth', '登录', '认证', '权限']):
                    logger.error("检测到认证失败，Cookie可能已过期")
                return False
            
        except requests.exceptions.Timeout:
            logger.error("请求超时，请检查网络连接")
            return False
        except requests.exceptions.RequestException as req_err:
            logger.error(f"请求失败: {req_err}")
            return False
        except Exception as e:
            logger.error(f"测试Cookie失败: {e}")
            return False
    
    def sync_from_api(self, azone: str, page: int = 1, per_page: int = 2000,
                     triggered_by: str = "system") -> Dict[str, Any]:
        """从API同步数据"""
        # 创建同步日志
        sync_log = CMDBSyncLog(
            sync_type="api",
            azone=azone,
            status="running",
            triggered_by=triggered_by
        )
        self.db.add(sync_log)
        self.db.commit()
        
        start_time = datetime.utcnow()
        
        try:
            # 获取Cookie
            cookie = self.get_cookie()
            if not cookie:
                raise Exception("AMIS Cookie未配置，请先配置Cookie")
            
            # 调用API
            headers = {
                "Cookie": cookie,
                "Referer": "https://amis.baidu.com/group/iaasops/bcc/hypervisor_vm_cross",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            params = {
                "page": page,
                "nova_host_azone": azone,
                "perPage": per_page
            }
            
            logger.info(f"开始从API同步CMDB数据: {azone}, page={page}, perPage={per_page}")
            response = requests.get(self.api_url, params=params, headers=headers, timeout=60)
            data = response.json()
            
            if data.get("status") != 0:
                raise Exception(f"API返回错误: {data.get('msg', '未知错误')}")
            
            rows = data.get("data", {}).get("rows", [])
            logger.info(f"获取到 {len(rows)} 条记录")
            
            # 同步数据
            servers_added = 0
            servers_updated = 0
            servers_skipped = 0  # 跳过的重复记录
            instances_added = 0
            instances_updated = 0
            instances_skipped = 0  # 跳过的重复记录
            
            # 用于跟踪本批次已处理的记录,避免重复
            processed_servers = {}  # hostname -> server对象
            processed_instances = {}  # instance_uuid -> instance对象
            
            for row in rows:
                # 同步服务器
                hostname = row.get("bns_hostname")
                if hostname:
                    # 先检查本批次是否已处理
                    if hostname in processed_servers:
                        server = processed_servers[hostname]
                        servers_skipped += 1
                        is_new = False
                        # 合并更新：如果新数据有非空字段，更新到已处理的记录中
                        self._merge_server_fields(server, row)
                    else:
                        # 查询数据库
                        server = self.db.query(IaasServer).filter(
                            IaasServer.bns_hostname == hostname
                        ).first()
                        
                        is_new = server is None
                        if is_new:
                            server = IaasServer(bns_hostname=hostname)
                            self.db.add(server)
                            servers_added += 1
                        else:
                            servers_updated += 1
                        
                        # 记录到本批次已处理
                        processed_servers[hostname] = server
                    
                    # 更新所有字段
                    self._update_server_fields(server, row)
                    server.synced_at = datetime.utcnow()
                
                # 同步实例
                instance_uuid = row.get("nova_vm_instance_uuid")
                if instance_uuid:
                    # 先检查本批次是否已处理
                    if instance_uuid in processed_instances:
                        instance = processed_instances[instance_uuid]
                        instances_skipped += 1
                        is_new = False
                        # 合并更新：如果新数据有非空字段，更新到已处理的记录中
                        self._merge_instance_fields(instance, row)
                    else:
                        # 查询数据库
                        instance = self.db.query(IaasInstance).filter(
                            IaasInstance.nova_vm_instance_uuid == instance_uuid
                        ).first()
                        
                        is_new = instance is None
                        if is_new:
                            instance = IaasInstance(nova_vm_instance_uuid=instance_uuid)
                            self.db.add(instance)
                            instances_added += 1
                        else:
                            instances_updated += 1
                        
                        # 记录到本批次已处理
                        processed_instances[instance_uuid] = instance
                    
                    # 更新所有字段
                    self._update_instance_fields(instance, row)
                    instance.synced_at = datetime.utcnow()
            
            self.db.commit()
            
            # 更新同步日志
            end_time = datetime.utcnow()
            sync_log.status = "success"
            sync_log.total_rows = len(rows)
            sync_log.servers_added = servers_added
            sync_log.servers_updated = servers_updated
            sync_log.instances_added = instances_added
            sync_log.instances_updated = instances_updated
            sync_log.completed_at = end_time
            sync_log.duration_seconds = int((end_time - start_time).total_seconds())
            self.db.commit()
            
            # 日志中包含跳过的记录数
            if servers_skipped > 0 or instances_skipped > 0:
                logger.info(f"同步完成: 服务器(新增{servers_added}/更新{servers_updated}/跳过{servers_skipped}), 实例(新增{instances_added}/更新{instances_updated}/跳过{instances_skipped})")
            else:
                logger.info(f"同步完成: 服务器(新增{servers_added}/更新{servers_updated}), 实例(新增{instances_added}/更新{instances_updated})")
            
            return {
                "success": True,
                "azone": azone,
                "total_rows": len(rows),
                "servers_added": servers_added,
                "servers_updated": servers_updated,
                "instances_added": instances_added,
                "instances_updated": instances_updated,
                "duration_seconds": sync_log.duration_seconds
            }
            
        except Exception as e:
            # 显式回滚事务
            self.db.rollback()
            
            # 更新同步日志为失败
            end_time = datetime.utcnow()
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = end_time
            sync_log.duration_seconds = int((end_time - start_time).total_seconds())
            self.db.commit()
            
            logger.error(f"同步失败: {e}")
            raise
    
    
    def _merge_server_fields(self, server: IaasServer, row: Dict):
        """合并服务器字段 - 只更新新数据中的非空字段"""
        # BNS字段
        for field in ["bns_id", "bns_serviceunit", "bns_ip", "bns_instancename", "bns_product"]:
            if field in row and row[field] and not getattr(server, field, None):
                setattr(server, field, row[field])
        
        # RMS字段
        rms_fields = [
            "rms_hostname", "rms_sn", "rms_cabinetsn", "rms_server_id", "rms_suit",
            "rms_type", "rms_status", "rms_model", "rms_rack_info", "rms_manufacturer",
            "rms_idc", "rms_product", "rms_kernel", "rms_department", "rms_ilo_ip",
            "rms_ilo_mac", "rms_ip_in1", "rms_ip_in2", "rms_ip_out", "rms_mac1",
            "rms_mac2", "rms_cpu", "rms_flash", "rms_harddisk", "rms_memory",
            "rms_networkcard", "rms_raid", "rms_ssd"
        ]
        for field in rms_fields:
            if field in row and row[field] and not getattr(server, field, None):
                setattr(server, field, row[field])
        
        # Nova Host字段 - 这些字段总是更新（可能变化）
        nova_host_fields = [
            "nova_host_physical_memory_mb_free", "nova_host_physical_disk_gb_free",
            "nova_host_vcpus_used", "nova_host_vcpus_free", "nova_host_running_vms"
        ]
        for field in nova_host_fields:
            if field in row and row[field] is not None:
                setattr(server, field, row[field])
    
    def _merge_instance_fields(self, instance: IaasInstance, row: Dict):
        """合并实例字段 - 只更新新数据中的非空字段"""
        # 关联字段
        if "bns_hostname" in row and row["bns_hostname"] and not instance.bns_hostname:
            instance.bns_hostname = row["bns_hostname"]
        
        # 状态字段总是更新（可能变化）
        state_fields = ["nova_vm_power_state", "nova_vm_task_state", "nova_vm_vm_state"]
        for field in state_fields:
            if field in row and row[field] is not None:
                setattr(instance, field, row[field])
        
        # 其他字段只在为空时更新
        nova_vm_fields = [
            "nova_vm_display_name", "nova_vm_hypervisor_hostname", "nova_vm_cluster",
            "nova_vm_azone", "nova_vm_user_id", "nova_vm_tenant_id", "nova_vm_metadata_source",
            "nova_vm_os_type", "nova_vm_flavor_id", "nova_vm_vcpus", "nova_vm_memory_mb",
            "nova_vm_root_gb", "nova_vm_ephemeral_gb"
        ]
        for field in nova_vm_fields:
            if field in row and row[field] and not getattr(instance, field, None):
                setattr(instance, field, row[field])
    
    def _update_server_fields(self, server: IaasServer, row: Dict):
        """更新服务器字段"""
        # BNS字段
        for field in ["bns_id", "bns_serviceunit", "bns_ip", "bns_instancename", "bns_product"]:
            if field in row:
                setattr(server, field, row[field])
        
        # RMS字段
        rms_fields = [
            "rms_hostname", "rms_sn", "rms_cabinetsn", "rms_server_id", "rms_suit",
            "rms_type", "rms_status", "rms_model", "rms_rack_info", "rms_manufacturer",
            "rms_idc", "rms_product", "rms_kernel", "rms_department", "rms_ilo_ip",
            "rms_ilo_mac", "rms_ip_in1", "rms_ip_in2", "rms_ip_out", "rms_mac1",
            "rms_mac2", "rms_cpu", "rms_flash", "rms_harddisk", "rms_memory",
            "rms_networkcard", "rms_raid", "rms_ssd"
        ]
        for field in rms_fields:
            if field in row:
                setattr(server, field, row[field])
        
        # RMS时间字段
        for field in ["rms_arrive_time", "rms_online_time", "rms_mod_time", "rms_maintenance_time"]:
            if field in row and row[field]:
                try:
                    setattr(server, field, datetime.fromisoformat(row[field].replace('Z', '+00:00')))
                except:
                    pass
        
        # Nova Host字段
        nova_host_fields = [
            "nova_host_hypervisor_id", "nova_host_hypervisor_hostname", "nova_host_cluster",
            "nova_host_node_type", "nova_host_node_state", "nova_host_azone", "nova_host_group_id",
            "nova_host_model", "nova_host_logical_machine_suit", "nova_host_machine_suit",
            "nova_host_hypervisor_type", "nova_host_physical_memory_mb_total",
            "nova_host_physical_memory_mb_free", "nova_host_physical_disk_gb_free",
            "nova_host_vcpus_total", "nova_host_vcpus_used", "nova_host_vcpus_free",
            "nova_host_running_vms", "nova_host_physical_cpus", "nova_host_host_ip",
            "nova_host_hypervisor_version", "nova_host_net_bandwidth_kbps",
            "nova_host_service_id", "nova_host_blacklisted_description",
            "nova_host_blacklisted_reason"
        ]
        for field in nova_host_fields:
            if field in row:
                setattr(server, field, row[field])
        
        # Nova Host时间字段
        for field in ["nova_host_blacklisted_expired_at", "nova_host_arrive_time"]:
            if field in row and row[field]:
                try:
                    setattr(server, field, datetime.fromisoformat(row[field].replace('Z', '+00:00')))
                except:
                    pass
        
        # JSON字段
        for field in ["nova_host_cpu_info", "nova_host_disks"]:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    setattr(server, field, row[field])
                else:
                    setattr(server, field, json.dumps(row[field], ensure_ascii=False))
    
    def _update_instance_fields(self, instance: IaasInstance, row: Dict):
        """更新实例字段"""
        # 关联字段
        if "bns_hostname" in row:
            instance.bns_hostname = row["bns_hostname"]
        
        # Nova VM字段
        nova_vm_fields = [
            "nova_vm_display_name", "nova_vm_hypervisor_hostname", "nova_vm_cluster",
            "nova_vm_azone", "nova_vm_user_id", "nova_vm_tenant_id", "nova_vm_metadata_source",
            "nova_vm_os_type", "nova_vm_flavor_id", "nova_vm_vcpus", "nova_vm_memory_mb",
            "nova_vm_root_gb", "nova_vm_ephemeral_gb", "nova_vm_project_id",
            "nova_vm_instance_name", "nova_vm_image_uuid", "nova_vm_max_net_bandwidth_kbps",
            "nova_vm_power_state", "nova_vm_task_state", "nova_vm_vm_state"
        ]
        for field in nova_vm_fields:
            if field in row:
                setattr(instance, field, row[field])
        
        # Nova VM时间字段
        for field in ["nova_vm_created_at", "nova_vm_launched_at"]:
            if field in row and row[field]:
                try:
                    setattr(instance, field, datetime.fromisoformat(row[field].replace('Z', '+00:00')))
                except:
                    pass
        
        # JSON字段
        for field in ["nova_vm_subnets", "nova_vm_floating_ips", "nova_vm_fixed_ips",
                     "nova_vm_virtual_disks", "nova_vm_volumes_attached"]:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    setattr(instance, field, row[field])
                else:
                    setattr(instance, field, json.dumps(row[field], ensure_ascii=False))
        
        # CRM字段
        crm_fields = ["crm_accountId", "crm_loginName", "crm_company", "crm_vip_type"]
        for field in crm_fields:
            if field in row:
                setattr(instance, field, row[field])
        
        # CRM JSON字段
        if "crm_tags" in row and row["crm_tags"]:
            if isinstance(row["crm_tags"], str):
                instance.crm_tags = row["crm_tags"]
            else:
                instance.crm_tags = json.dumps(row["crm_tags"], ensure_ascii=False)
    
    def get_sync_logs(self, limit: int = 20) -> List[CMDBSyncLog]:
        """获取同步日志"""
        return self.db.query(CMDBSyncLog).order_by(
            CMDBSyncLog.started_at.desc()
        ).limit(limit).all()
