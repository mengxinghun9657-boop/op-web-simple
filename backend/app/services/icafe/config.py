#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
icafe 配置管理模块
"""

import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger


@dataclass
class IcafeConfig:
    """icafe 配置"""
    # API 配置
    base_url: str = "http://icafeapi.baidu-int.com/api/spaces"
    timeout: int = 30
    max_page_limit: int = 100
    max_total_records: int = 10000
    
    # 默认查询参数
    default_spacecode: str = "HMLCC"
    default_username: str = ""
    default_password: str = ""
    default_page: int = 1
    default_pgcount: int = 100
    default_iql_template: str = "创建时间 > {start_date} AND 创建时间 < {end_date}"
    
    # 分析配置
    target_users: list = field(default_factory=list)  # 空列表表示分析所有负责人
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "IcafeConfig":
        """从配置文件和环境变量加载配置"""
        config = cls()
        
        # 1. 优先从系统配置数据库加载
        try:
            config._load_from_system_config()
            logger.info("已从系统配置数据库加载 iCafe 配置")
        except Exception as e:
            logger.warning(f"从系统配置加载失败: {e}，尝试从配置文件加载")
            
            # 2. 降级到配置文件加载
            if config_path is None:
                config_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                    'config', 'icafe.json'
                )
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                    config._apply_dict(file_config)
                    logger.info(f"已加载 icafe 配置文件: {config_path}")
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {e}，使用默认配置")

        # 3. 环境变量覆盖
        env_mappings = {
            'ICAFE_BASE_URL': 'base_url',
            'ICAFE_TIMEOUT': ('timeout', int),
            'ICAFE_MAX_PAGE_LIMIT': ('max_page_limit', int),
            'ICAFE_MAX_TOTAL_RECORDS': ('max_total_records', int),
            'ICAFE_DEFAULT_SPACECODE': 'default_spacecode',
            'ICAFE_DEFAULT_USERNAME': 'default_username',
            'ICAFE_DEFAULT_PASSWORD': 'default_password',
            'ICAFE_DEFAULT_PAGE': ('default_page', int),
            'ICAFE_DEFAULT_PGCOUNT': ('default_pgcount', int),
        }
        
        for env_key, attr_info in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value:
                if isinstance(attr_info, tuple):
                    attr_name, converter = attr_info
                    setattr(config, attr_name, converter(env_value))
                else:
                    setattr(config, attr_info, env_value)
        
        return config
    
    def _load_from_system_config(self):
        """从系统配置数据库加载配置"""
        try:
            # 导入数据库相关模块
            from app.core.database import SessionLocal
            from app.models.system_config import SystemConfig
            
            db = SessionLocal()
            try:
                # 查询 iCafe 配置
                icafe_config_record = db.query(SystemConfig).filter(
                    SystemConfig.module == 'icafe',
                    SystemConfig.config_key == 'main'
                ).first()
                
                if icafe_config_record and icafe_config_record.config_value:
                    config_data = icafe_config_record.config_value
                    
                    # 如果 config_value 是字符串（JSON），解析为字典
                    if isinstance(config_data, str):
                        try:
                            config_data = json.loads(config_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"解析 iCafe 配置 JSON 失败: {e}")
                            raise Exception(f"配置格式错误: {e}")
                    
                    # 映射系统配置到 iCafe 配置
                    if isinstance(config_data, dict) and config_data.get('api_url'):
                        # 转换 API URL 格式
                        api_url = config_data['api_url']
                        if api_url.endswith('/api/v2'):
                            # 从 http://icafeapi.baidu-int.com/api/v2 转换为 http://icafeapi.baidu-int.com/api/spaces
                            self.base_url = api_url.replace('/api/v2', '/api/spaces')
                        else:
                            self.base_url = api_url
                    
                    if config_data.get('space_id'):
                        self.default_spacecode = config_data['space_id']
                    
                    if config_data.get('username'):
                        self.default_username = config_data['username']
                    
                    if config_data.get('password'):
                        self.default_password = config_data['password']
                    
                    logger.info("✅ 成功从系统配置加载 iCafe 配置")
                else:
                    logger.warning("系统配置中未找到 iCafe 配置")
                    
            finally:
                db.close()
                
        except ImportError:
            # 如果无法导入数据库模块（如在测试环境），跳过
            logger.debug("无法导入数据库模块，跳过系统配置加载")
            raise Exception("数据库模块不可用")
        except Exception as e:
            logger.error(f"从系统配置加载 iCafe 配置失败: {e}")
            raise
    
    def _apply_dict(self, d: dict):
        """应用字典配置"""
        for key, value in d.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_default_iql(self) -> str:
        """获取默认 IQL 查询语句（当前月份）"""
        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        
        if now.month == 12:
            end_year, end_month = now.year + 1, 1
        else:
            end_year, end_month = now.year, now.month + 1
        
        from datetime import timedelta
        next_month_first = datetime(end_year, end_month, 1)
        last_day = (next_month_first - timedelta(days=1)).day
        end_date = f"{now.year}-{now.month:02d}-{last_day}"
        
        return self.default_iql_template.format(start_date=start_date, end_date=end_date)
    
    def to_dict(self) -> dict:
        """转换为字典（用于 API 响应，不包含密码）"""
        return {
            'base_url': self.base_url,
            'timeout': self.timeout,
            'max_page_limit': self.max_page_limit,
            'max_total_records': self.max_total_records,
            'default_spacecode': self.default_spacecode,
            'default_username': self.default_username,
            'default_page': self.default_page,
            'default_pgcount': self.default_pgcount,
            'default_iql': self.get_default_iql()
        }


# 全局配置实例
_config: Optional[IcafeConfig] = None


def get_icafe_config() -> IcafeConfig:
    """获取 icafe 配置单例"""
    global _config
    if _config is None:
        _config = IcafeConfig.load()
    return _config


def reload_icafe_config() -> IcafeConfig:
    """重新加载 icafe 配置（用于配置更新后刷新）"""
    global _config
    _config = None  # 清除缓存
    _config = IcafeConfig.load()
    logger.info("✅ iCafe 配置已重新加载")
    return _config
