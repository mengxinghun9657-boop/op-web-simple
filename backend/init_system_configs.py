#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化系统配置
添加监控和分析的默认配置到system_config表
"""

import sys
import os
import json
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.system_config import SystemConfig
from loguru import logger
from sqlalchemy import text


def load_default_configs():
    """从JSON文件加载默认配置"""
    config_file = os.path.join(os.path.dirname(__file__), 'config', 'default_instance_ids.json')

    if not os.path.exists(config_file):
        logger.error(f"❌ 配置文件不存在: {config_file}")
        logger.error(f"   当前工作目录: {os.getcwd()}")
        logger.error(f"   脚本目录: {os.path.dirname(__file__)}")
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)

        # 验证配置文件内容
        required_keys = ['resource_analysis', 'eip_monitoring', 'bcc_monitoring', 'bos_monitoring']
        missing_keys = [key for key in required_keys if key not in configs]

        if missing_keys:
            logger.error(f"❌ 配置文件缺少必需字段: {missing_keys}")
            raise ValueError(f"配置文件格式错误，缺少字段: {missing_keys}")

        # 检查是否所有配置都为空
        all_empty = all(not configs.get(key) for key in required_keys)
        if all_empty:
            logger.error("❌ 配置文件所有字段都为空")
            raise ValueError("配置文件无效，所有配置项都为空")

        logger.info(f"✅ 成功加载配置文件: {config_file}")
        logger.info(f"   - 资源分析集群数: {len(configs.get('resource_analysis', []))}")
        logger.info(f"   - EIP监控实例数: {len(configs.get('eip_monitoring', []))}")
        logger.info(f"   - BCC监控实例数: {len(configs.get('bcc_monitoring', []))}")
        logger.info(f"   - BOS监控Bucket数: {len(configs.get('bos_monitoring', []))}")

        return configs

    except json.JSONDecodeError as e:
        logger.error(f"❌ 配置文件JSON格式错误: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 加载配置文件失败: {e}")
        raise


def init_system_configs():
    """初始化系统配置"""

    # 带重试的数据库连接（与故障手册导入脚本一致）
    db = None
    for attempt in range(10):  # 最多重试10次
        try:
            db = SessionLocal()
            # 测试连接
            db.execute(text("SELECT 1"))
            logger.info(f"✅ 数据库连接成功 (尝试 {attempt+1}/10)")
            break
        except Exception as e:
            if db:
                db.close()
                db = None

            if attempt < 9:
                logger.warning(f"⚠️  数据库连接失败（尝试 {attempt+1}/10）: {str(e)[:100]}，等待5秒后重试...")
                time.sleep(5)
            else:
                logger.error(f"❌ 数据库连接失败（已重试10次）: {str(e)[:200]}")
                logger.error("   可能原因：")
                logger.error("   1. MySQL 正在处理大量写入（故障手册导入）")
                logger.error("   2. 连接池已满，gunicorn workers 正在启动")
                logger.error("   建议：")
                logger.error("   - 稍后手动执行: docker compose -f docker-compose.prod.yml exec backend python3 init_system_configs.py")
                logger.error("   - 或重启后端服务: docker compose -f docker-compose.prod.yml restart backend")
                raise

    if not db:
        logger.error("❌ 无法建立数据库连接")
        raise Exception("数据库连接失败")

    try:
        logger.info("开始初始化系统配置...")

        # 加载配置
        configs = load_default_configs()

        # 1. 监控配置
        monitoring_config = {
            'eip_instance_ids': ','.join(configs.get('eip_monitoring', [])),  # 转换为逗号分隔字符串
            'eip_description': 'EIP监控默认实例ID列表',
            'bcc_instance_ids': ','.join(configs.get('bcc_monitoring', [])),  # 转换为逗号分隔字符串
            'bcc_description': 'BCC监控默认实例ID列表',
            'bos_bucket_names': ','.join(configs.get('bos_monitoring', [])),  # 转换为逗号分隔字符串
            'bos_description': 'BOS监控默认Bucket列表'
        }
        
        # 检查监控配置是否已存在
        existing_monitoring = db.query(SystemConfig).filter(
            SystemConfig.module == 'monitoring',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_monitoring:
            # 检查是否需要更新配置（如果配置为空或缺少默认值）
            try:
                current_config = json.loads(existing_monitoring.config_value) if existing_monitoring.config_value else {}
                needs_update = False
                
                # 检查关键字段是否为空
                for key in ['eip_instance_ids', 'bcc_instance_ids', 'bos_bucket_names']:
                    if not current_config.get(key) or current_config.get(key) == '':
                        needs_update = True
                        break
                
                if needs_update:
                    logger.info("监控配置存在但为空，更新默认值...")
                    existing_monitoring.config_value = json.dumps(monitoring_config, ensure_ascii=False)
                    existing_monitoring.updated_by = 1
                    eip_count = len(configs.get('eip_monitoring', []))
                    bcc_count = len(configs.get('bcc_monitoring', []))
                    bos_count = len(configs.get('bos_monitoring', []))
                    logger.info(f"✅ 更新监控配置: EIP={eip_count}, BCC={bcc_count}, BOS={bos_count}")
                else:
                    logger.info("监控配置已存在且有效，跳过")
            except json.JSONDecodeError:
                logger.warning("监控配置格式错误，重新创建...")
                existing_monitoring.config_value = json.dumps(monitoring_config, ensure_ascii=False)
                existing_monitoring.updated_by = 1
                eip_count = len(configs.get('eip_monitoring', []))
                bcc_count = len(configs.get('bcc_monitoring', []))
                bos_count = len(configs.get('bos_monitoring', []))
                logger.info(f"✅ 修复监控配置: EIP={eip_count}, BCC={bcc_count}, BOS={bos_count}")
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
            'cluster_ids': ','.join(configs.get('resource_analysis', [])),  # 转换为逗号分隔字符串
            'description': '资源分析默认集群ID列表'
        }

        # 2.1 Prometheus 统一配置
        prometheus_runtime_config = {
            'grafana_url': 'https://cprom.cd.baidubce.com/select/prometheus',
            'token': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lc3BhY2UiOiJjcHJvbS1qNWkxMm94dXFqMXo3Iiwic2VjcmV0TmFtZSI6ImYwMDhkYjQ3NTE4OTRhZmU5Yjg1MWUzMmEyMDY4MzM1IiwiZXhwIjo0ODk3MjczNTI2LCJpc3MiOiJjcHJvbSJ9.wbsW3Cs3PkTfgx_lsBHONGFqY7CFENSU-2NXChlT304',
            'instance_id': 'cprom-j5i12oxuqj1z7',
            'cluster_ids': ','.join(configs.get('resource_analysis', [])),
            'step': '5m'
        }
        
        # 检查分析配置是否已存在
        existing_analysis = db.query(SystemConfig).filter(
            SystemConfig.module == 'analysis',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_analysis:
            # 检查是否需要更新配置（如果配置为空或缺少默认值）
            try:
                current_config = json.loads(existing_analysis.config_value) if existing_analysis.config_value else {}
                if not current_config.get('cluster_ids') or current_config.get('cluster_ids') == '':
                    logger.info("分析配置存在但为空，更新默认值...")
                    existing_analysis.config_value = json.dumps(analysis_config, ensure_ascii=False)
                    existing_analysis.updated_by = 1
                    cluster_count = len(configs.get('resource_analysis', []))
                    logger.info(f"✅ 更新分析配置: 集群数={cluster_count}")
                else:
                    logger.info("分析配置已存在且有效，跳过")
            except json.JSONDecodeError:
                logger.warning("分析配置格式错误，重新创建...")
                existing_analysis.config_value = json.dumps(analysis_config, ensure_ascii=False)
                existing_analysis.updated_by = 1
                cluster_count = len(configs.get('resource_analysis', []))
                logger.info(f"✅ 修复分析配置: 集群数={cluster_count}")
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

        existing_runtime = db.query(SystemConfig).filter(
            SystemConfig.module == 'prometheus_runtime',
            SystemConfig.config_key == 'main'
        ).first()
        if existing_runtime:
            logger.info("Prometheus 统一配置已存在，跳过")
        else:
            runtime_record = SystemConfig(
                module='prometheus_runtime',
                config_key='main',
                config_value=json.dumps(prometheus_runtime_config, ensure_ascii=False),
                updated_by=1
            )
            db.add(runtime_record)
            logger.info("✅ 创建 Prometheus 统一配置")
        
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
        
        # 4. iCafe配置（空配置，需要管理员手动配置）
        icafe_config = {
            'api_url': 'http://icafeapi.baidu-int.com/api/v2',
            'space_id': 'HMLCC',
            'username': '',
            'password': '',
            'description': 'iCafe API配置，需要管理员在系统配置页面设置用户名和密码'
        }
        
        # 检查iCafe配置是否已存在
        existing_icafe = db.query(SystemConfig).filter(
            SystemConfig.module == 'icafe',
            SystemConfig.config_key == 'main'
        ).first()
        
        if existing_icafe:
            logger.info("iCafe配置已存在，跳过")
        else:
            # 创建iCafe配置
            icafe_record = SystemConfig(
                module='icafe',
                config_key='main',
                config_value=json.dumps(icafe_config, ensure_ascii=False),
                updated_by=1  # 系统管理员ID
            )
            db.add(icafe_record)
            logger.info("✅ 创建iCafe配置（空配置，需要管理员手动设置用户名和密码）")
        
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
