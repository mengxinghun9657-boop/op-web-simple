#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
icafe API 客户端
负责与 icafeapi.baidu-int.com 通信
"""

import requests
import json
import pandas as pd
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from loguru import logger

from .config import IcafeConfig, get_icafe_config


# iCafe API v2 URL 常量
ICAFE_API_V2_URL = "http://icafeapi.baidu-int.com/api/v2"


class IcafeAPIClient:
    """icafe API 客户端"""
    
    def __init__(self, config: Optional[IcafeConfig] = None):
        self.config = config or get_icafe_config()
    
    def _mask_password(self, password: str) -> str:
        """密码脱敏"""
        if not password:
            return ""
        if len(password) <= 4:
            return "****"
        return password[:2] + "****" + password[-2:]

    def _fix_plan_iql(self, iql: str) -> str:
        """
        修复 IQL 中所属计划字段的值格式。
        iCafe 要求 所属计划 的值为 "年份/季度" 格式（如 "2026/2026Q2"），
        用户常输入简写（如 "2026Q2"），此方法自动补全。
        """
        import re

        def replace_plan(m):
            val = m.group(1).strip().strip('"').strip("'")
            # YYYYQN 简写 → YYYY/YYYYQN
            if re.match(r'^\d{4}Q\d$', val, re.IGNORECASE):
                val = f'{val[:4]}/{val}'
            return f'所属计划 = "{val}"'

        return re.sub(r'所属计划\s*=\s*"?([^"\s\)]+)"?', replace_plan, iql)
    
    def fetch_data(
        self,
        spacecode: str,
        username: str,
        password: str,
        iql: str,
        page: int = 1,
        pgcount: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        获取 icafe 数据，支持自动分页
        
        Args:
            spacecode: 空间代码
            username: 用户名
            password: 密码
            iql: IQL 查询语句
            page: 起始页码
            pgcount: 每页记录数
            
        Returns:
            包含所有数据的字典，失败返回 None
        """
        try:
            # 日志记录（密码脱敏）
            logger.info(f"开始获取 API 数据: spacecode={spacecode}, page={page}, pgcount={pgcount}")
            logger.info(f"用户名: {username}, 密码: {self._mask_password(password)}")
            logger.info(f"IQL: {iql}")

            # 预处理 IQL：将 所属计划 = "2026Q2" 补全为 "2026/2026Q2"
            iql = self._fix_plan_iql(iql)
            logger.info(f"IQL (预处理后): {iql}")
            
            url = f"{self.config.base_url}/{spacecode}/cards"
            logger.info(f"API 请求 URL: {url}")
            
            all_cards = []
            current_page = int(page)
            
            while current_page <= self.config.max_page_limit:
                logger.debug(f"请求第 {current_page} 页数据")

                # 请求参数 - 手动编码特殊字符
                params = {
                    'u': username,
                    'pw': password,
                    'iql': iql,
                    'page': current_page,
                    'maxRecords': pgcount
                }
                
                # 发送请求（禁用自动编码，手动处理）
                # 构建查询字符串，确保特殊字符正确编码
                query_parts = []
                for key, value in params.items():
                    encoded_value = quote(str(value), safe='')
                    query_parts.append(f"{key}={encoded_value}")
                query_string = '&'.join(query_parts)
                full_url = f"{url}?{query_string}"
                
                # 日志中不记录完整URL，避免密码泄漏
                logger.debug(f"请求第 {current_page} 页: spacecode={spacecode}, iql={iql[:50]}...")
                response = requests.get(full_url, timeout=self.config.timeout)
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"API 响应状态: {data.get('result')}")
                
                if data.get('result') != 'success':
                    error_msg = f"API 返回错误: {data.get('message', '未知错误')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                cards = data.get('cards', [])
                all_cards.extend(cards)
                logger.info(f"第 {current_page} 页获取到 {len(cards)} 条记录，累计 {len(all_cards)} 条")
                
                # 检查是否还有更多数据
                total = int(data.get('total', 0)) if data.get('total') is not None else 0
                page_size = int(data.get('pageSize', 1)) if data.get('pageSize') is not None else 1
                
                logger.debug(f"API 返回信息: total={total}, pageSize={page_size}, currentPage={current_page}")
                
                # 检查记录数限制
                if len(all_cards) >= self.config.max_total_records:
                    logger.warning(f"达到最大记录数限制 {self.config.max_total_records}，停止获取")
                    break
                
                # 检查是否已获取所有数据
                # API 返回的 total 是总记录数，pageSize 是当前页的记录数
                total_records = int(data.get('total', 0)) if data.get('total') is not None else 0
                current_records = len(all_cards)
                
                logger.debug(f"API 返回信息: total={total_records}, currentRecords={current_records}, pageSize={page_size}")
                
                # 如果已获取的记录数 >= 总记录数，说明已获取所有数据
                if current_records >= total_records:
                    logger.info(f"已获取所有数据，当前记录数 {current_records}，总记录数 {total_records}")
                    break
                
                # 如果当前页没有数据，也停止
                if len(cards) == 0:
                    logger.info("当前页无数据，停止获取")
                    break
                
                current_page += 1
            
            logger.info(f"API 数据获取完成，总计 {len(all_cards)} 条记录")
            
            return {
                'result': 'success',
                'total': len(all_cards),
                'cards': all_cards
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"API 请求超时 (timeout={self.config.timeout}s)"
            logger.error(error_msg)
            return None
        except requests.exceptions.ConnectionError as e:
            error_msg = f"无法连接到 icafe API: {str(e)}"
            logger.error(error_msg)
            return None
        except requests.exceptions.HTTPError as e:
            error_body = ""
            try:
                error_body = e.response.text[:500]
            except Exception:
                pass
            error_msg = f"HTTP 错误: {str(e)}, 响应内容: {error_body}"
            logger.error(error_msg)
            return None
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"获取 API 数据失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None

    def _get_property_value(self, card: Dict, property_name: str) -> str:
        """从卡片的 properties 中获取指定属性值"""
        properties = card.get('properties', [])
        for prop in properties:
            if prop.get('propertyName') == property_name:
                return prop.get('displayValue', '')
        return ''
    
    def _get_responsible_people(self, card: Dict) -> str:
        """获取负责人列表"""
        people = card.get('responsiblePeople', [])
        if isinstance(people, list):
            names = [p.get('name', '') for p in people if isinstance(p, dict)]
            return ', '.join(names)
        return ''
    
    def convert_to_excel(self, api_data: Dict[str, Any], output_path: str) -> bool:
        """
        将 API 数据转换为 Excel 格式
        
        Args:
            api_data: API 返回的数据
            output_path: 输出文件路径
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            cards = api_data.get('cards', [])
            if not cards:
                logger.warning("API 数据为空，无法转换")
                return False
            
            logger.info(f"开始转换 {len(cards)} 条记录为 Excel")
            
            # 构建数据行
            rows = []
            for card in cards:
                row = {
                    '编号': card.get('sequence', ''),
                    '标题': card.get('title', ''),
                    '流程状态': card.get('status', ''),
                    '类型': card.get('type', {}).get('name', '') if isinstance(card.get('type'), dict) else '',
                    '负责人': self._get_responsible_people(card),
                    '创建时间': card.get('createdTime', ''),
                    # 预留列 (G-Q)
                    '列G': '', '列H': '', '列I': '', '列J': '', '列K': '',
                    '列L': '', '列M': '', '列N': '', '列O': '', '列P': '', '列Q': '',
                    # R列: 方向大类
                    '方向大类': self._get_property_value(card, '方向大类'),
                    # S列: 汇总分类
                    '汇总分类': self._get_property_value(card, '汇总分类'),
                    # T列: 细分分类
                    '细分分类': self._get_property_value(card, '细分分类'),
                }
                rows.append(row)
            
            # 创建 DataFrame
            df = pd.DataFrame(rows)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存为 Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"Excel 文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"转换 Excel 失败: {e}", exc_info=True)
            return False
    
    def get_default_params(self) -> Dict[str, Any]:
        """获取默认查询参数"""
        return {
            'spacecode': self.config.default_spacecode,
            'username': self.config.default_username,
            'password': self.config.default_password,
            'iql': self.config.get_default_iql(),
            'page': self.config.default_page,
            'pgcount': self.config.default_pgcount
        }

    def create_card(
        self,
        spacecode: str,
        username: str,
        password: str,
        title: str,
        detail: str,
        card_type: str = "Bug",
        fields: Optional[Dict[str, Any]] = None,
        creator: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建 iCafe 卡片
        
        Args:
            spacecode: 空间代码
            username: 用户名
            password: 密码
            title: 卡片标题
            detail: 卡片详情（HTML 格式）
            card_type: 卡片类型（Bug/Task/Requirement 等）
            fields: 自定义字段字典
            creator: 创建人（默认使用 username）
            comment: 评论内容
            
        Returns:
            创建结果字典，失败返回 None
        """
        try:
            logger.info(f"开始创建卡片: spacecode={spacecode}, title={title}")
            logger.info(f"用户名: {username}, 密码: {self._mask_password(password)}")
            
            url = f"{ICAFE_API_V2_URL}/space/{spacecode}/issue/new"
            logger.info(f"API 请求 URL: {url}")
            
            # 构建请求 payload
            payload = {
                "username": username,
                "password": password,
                "issues": [{
                    "title": title,
                    "detail": detail,
                    "type": card_type,
                    "fields": fields or {},
                    "creator": creator or username,
                    "comment": comment or ""
                }]
            }
            
            logger.debug(f"请求 payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"API 响应状态: {result.get('status')}")
            
            if result.get('status') == 200:
                logger.success(f"✅ 卡片创建成功！编号: {result.get('issueSequences', [None])[0]}")
                return {
                    'success': True,
                    'message': '卡片创建成功',
                    'data': result
                }
            else:
                error_msg = f"卡片创建失败: {result.get('message', '未知错误')}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'message': result.get('message', '未知错误'),
                    'data': result
                }
                
        except requests.exceptions.Timeout:
            error_msg = f"API 请求超时 (timeout={self.config.timeout}s)"
            logger.error(error_msg)
            return None
        except requests.exceptions.ConnectionError as e:
            error_msg = f"无法连接到 icafe API: {str(e)}"
            logger.error(error_msg)
            return None
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP 错误: {str(e)}"
            logger.error(error_msg)
            return None
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失败: {str(e)}"
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"创建卡片失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None
# iCafe API v2 URL 常量
ICAFE_API_V2_URL = "http://icafeapi.baidu-int.com/api/v2"
