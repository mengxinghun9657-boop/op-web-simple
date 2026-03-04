#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化路由规则

创建初始的路由规则，用于优化 SQL 生成的表选择
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db_sync
from app.services.ai.routing_rule_manager import RoutingRuleManager
from app.core.logger import logger


async def init_routing_rules():
    """初始化路由规则"""
    
    logger.info("🚀 开始初始化路由规则...")
    
    # 获取数据库会话
    db = next(get_db_sync())
    
    try:
        # 创建 RoutingRuleManager
        rule_manager = RoutingRuleManager(db=db)
        
        # 规则 1: 物理机查询
        rule1 = {
            "pattern": "查询物理机信息、宿主机信息、服务器信息",
            "intent_type": "sql",
            "priority": 80,
            "description": "涉及物理机、宿主机、服务器的查询，使用 CMDB 的 iaas_servers 表",
            "metadata": {
                "recommended_tables": ["iaas_servers"],
                "recommended_database": "cmdb",
                "table_priority": {
                    "iaas_servers": 100,
                    "mydb.bce_cce_nodes": 10
                },
                "reason": "CMDB 表包含完整的物理机信息，包括 SN、IP、加黑状态等"
            }
        }
        
        # 规则 2: IP 地址查询
        rule2 = {
            "pattern": "IP地址所属查询、IP地址信息查询",
            "intent_type": "sql",
            "priority": 90,
            "description": "查询 IP 地址所属的物理机或虚机，优先使用 CMDB 表",
            "metadata": {
                "recommended_tables": ["iaas_servers", "iaas_instances"],
                "recommended_database": "cmdb",
                "table_priority": {
                    "iaas_servers": 100,
                    "iaas_instances": 90,
                    "mydb.bce_cce_nodes": 10
                },
                "reason": "IP 地址查询应该优先在 CMDB 表中查找"
            }
        }
        
        # 规则 3: 虚机实例查询
        rule3 = {
            "pattern": "虚拟机实例查询、虚机查询、实例信息查询",
            "intent_type": "sql",
            "priority": 85,
            "description": "查询虚拟机实例信息，使用 CMDB 的 iaas_instances 表",
            "metadata": {
                "recommended_tables": ["iaas_instances"],
                "recommended_database": "cmdb",
                "table_priority": {
                    "iaas_instances": 100,
                    "mydb.bce_bcc_instances": 10
                },
                "reason": "CMDB 表包含完整的虚机实例信息"
            }
        }
        
        # 规则 4: 集群查询
        rule4 = {
            "pattern": "集群信息查询、集群列表查询",
            "intent_type": "sql",
            "priority": 85,
            "description": "查询集群信息，使用 CMDB 的 iaas_clusters 表",
            "metadata": {
                "recommended_tables": ["iaas_clusters"],
                "recommended_database": "cmdb",
                "table_priority": {
                    "iaas_clusters": 100
                },
                "reason": "CMDB 表包含完整的集群信息"
            }
        }
        
        # 规则 5: 加黑状态查询
        rule5 = {
            "pattern": "加黑状态查询、黑名单查询",
            "intent_type": "sql",
            "priority": 85,
            "description": "查询加黑状态，使用 CMDB 的 iaas_servers 表",
            "metadata": {
                "recommended_tables": ["iaas_servers"],
                "recommended_database": "cmdb",
                "table_priority": {
                    "iaas_servers": 100
                },
                "reason": "加黑状态存储在 CMDB 的 iaas_servers 表中"
            }
        }
        
        # 创建规则
        rules = [rule1, rule2, rule3, rule4, rule5]
        
        for i, rule in enumerate(rules, 1):
            try:
                created_rule = await rule_manager.create_rule(
                    pattern=rule["pattern"],
                    intent_type=rule["intent_type"],
                    priority=rule["priority"],
                    description=rule["description"],
                    metadata=rule["metadata"]
                )
                logger.info(f"✅ 规则 {i} 创建成功: id={created_rule.id}, pattern={created_rule.pattern}")
            except Exception as e:
                logger.error(f"❌ 规则 {i} 创建失败: {e}")
        
        logger.info("✅ 路由规则初始化完成")
        
    except Exception as e:
        logger.error(f"❌ 初始化路由规则失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(init_routing_rules())
