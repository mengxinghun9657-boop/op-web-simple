#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化系统配置
添加监控和分析的默认配置到system_config表
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.system_config import SystemConfig
from loguru import logger


def load_default_configs():
    """从JSON文件加载默认配置"""
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'default_instance_ids.json')
    
    if not os.path.exists(config_file):
        logger.warning(f"配置文件不存在: {config_file}")
        return {}
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def init_system_configs():
    """初始化系统配置"""
    db = SessionLocal()
    try:
        logger.info("开始初始化系统配置...")
        
        # 加载配置
        configs = load_default_configs()
        
        if not configs:
            logger.warning("没有找到默认配置，跳过初始化")
            return
        
        # 1. 监控配置
        monitoring_config = {
            'eip_instance_ids': configs.get('eip_monitoring', []),
            'eip_description': 'EIP监控默认实例ID列表',
            'bcc_instance_ids': configs.get('bcc_monitoring', []),
            'bcc_description': 'BCC监控默认实例ID列表',
            'bos_bucket_names': configs.get('bos_monitoring', []),
            'bos_description': 'BOS监控默认Bucket列表'
        }
        
        # 检查监控配置是否已存在
        existing_monitoring = db.query(SystemConfig).filter(
            SystemConfig.module == 'monitoring',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_monitoring:
            logger.info("监控配置已存在，跳过")
        else:
            # 创建监控配置
            monitoring_record = SystemConfig(
                module='monitoring',
                config_key='main',
                config_value=json.dumps(monitoring_config, ensure_ascii=False),
                updated_by=1  # 系统管理员ID
            )
            db.add(monitoring_record)
            eip_count = len(configs.get('eip_monitoring', []))
            bcc_count = len(configs.get('bcc_monitoring', []))
            bos_count = len(configs.get('bos_monitoring', []))
            logger.info(f"✅ 创建监控配置: EIP={eip_count}, BCC={bcc_count}, BOS={bos_count}")
        
        # 2. 分析配置
        analysis_config = {
            'cluster_ids': configs.get('resource_analysis', []),
            'description': '资源分析默认集群ID列表'
        }
        
        # 检查分析配置是否已存在
        existing_analysis = db.query(SystemConfig).filter(
            SystemConfig.module == 'analysis',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_analysis:
            logger.info("分析配置已存在，跳过")
        else:
            # 创建分析配置
            analysis_record = SystemConfig(
                module='analysis',
                config_key='main',
                config_value=json.dumps(analysis_config, ensure_ascii=False),
                updated_by=1  # 系统管理员ID
            )
            db.add(analysis_record)
            cluster_count = len(configs.get('resource_analysis', []))
            logger.info(f"✅ 创建分析配置: 集群数={cluster_count}")
        
        # 3. CMDB配置（空配置，需要管理员手动配置Cookie）
        cmdb_config = {
            'api_cookie': '',
            'expires_at': None,
            'azone': '',
            'per_page': 100,
            'description': 'CMDB API配置，需要管理员在系统配置页面设置Cookie'
        }
        
        # 检查CMDB配置是否已存在
        existing_cmdb = db.query(SystemConfig).filter(
            SystemConfig.module == 'cmdb',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_cmdb:
            logger.info("CMDB配置已存在，跳过")
        else:
            # 创建CMDB配置
            cmdb_record = SystemConfig(
                module='cmdb',
                config_key='main',
                config_value=json.dumps(cmdb_config, ensure_ascii=False),
                updated_by=1  # 系统管理员ID
            )
            db.add(cmdb_record)
            logger.info("✅ 创建CMDB配置（空配置，需要管理员手动设置Cookie）")
        
        db.commit()
        logger.info("✅ 系统配置初始化完成")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 初始化系统配置失败: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    init_system_configs()
