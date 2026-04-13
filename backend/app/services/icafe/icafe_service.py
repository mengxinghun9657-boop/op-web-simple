#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
iCafe 卡片服务
"""

import requests
import json
from typing import Dict, Any, Optional
from loguru import logger


class ICafeService:
    """iCafe 卡片管理服务"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 iCafe 服务
        
        Args:
            config: iCafe 配置字典
                - api_url: API 地址
                - space_id: 空间ID
                - username: 用户名
                - password: 密码
        """
        self.api_url = config.get('api_url', 'http://icafeapi.baidu-int.com/api/v2')
        self.space_id = config.get('space_id', 'HMLCC')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
    
    def test_connection(self) -> tuple[bool, str]:
        """
        测试 iCafe API 连接

        Returns:
            tuple[bool, str]: (是否成功, 消息)
        """
        try:
            # 构造测试URL - 使用获取空间字段的API端点验证连接和权限
            test_url = f"{self.api_url}/spaces/{self.space_id}/fieldsForCreate"

            # iCafe API 使用查询参数传递认证信息（不支持 HTTP Basic Auth）
            params = {
                'username': self.username,
                'password': self.password,
                'issueTypeName': 'Bug'
            }

            headers = {"Content-Type": "application/json"}

            logger.info(f"测试 iCafe 连接: {test_url}")

            response = requests.get(
                test_url,
                headers=headers,
                params=params,
                timeout=10
            )
            
            # 检查 HTTP 状态
            if response.status_code != 200:
                logger.warning(f"❌ iCafe 连接失败: HTTP {response.status_code}")
                return False, f"连接失败：HTTP {response.status_code}"

            # 解析 iCafe API 响应（使用 JSON body 中的 status 字段判断）
            result = response.json()
            api_status = result.get('status')
            api_message = result.get('message', '')

            if api_status == 200:
                logger.success("✅ iCafe 连接测试成功")
                return True, "连接测试成功"
            elif api_status == 100:
                logger.warning("❌ iCafe 认证失败")
                return False, "认证失败：用户名或密码错误"
            elif api_status == 101:
                logger.warning("❌ iCafe 权限不足")
                return False, f"权限不足：用户 {self.username} 没有空间 {self.space_id} 的访问权限"
            elif api_status == 304:
                logger.warning("❌ iCafe 空间不存在")
                return False, f"空间 {self.space_id} 不存在"
            else:
                logger.warning(f"❌ iCafe 连接失败: status={api_status}, message={api_message}")
                return False, f"连接失败：{api_message}"
                
        except requests.exceptions.Timeout:
            logger.error("❌ iCafe 连接超时")
            return False, "连接超时：请检查网络连接和API地址"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ iCafe 连接错误: {e}")
            return False, f"连接错误：无法访问 {self.api_url}"
        except Exception as e:
            logger.error(f"❌ iCafe 连接测试失败: {e}")
            return False, f"测试失败：{str(e)}"

    def _send_create_request(self, card_data: Dict[str, Any], fields: Dict[str, Any]) -> Dict[str, Any]:
        """发送创建卡片请求"""
        url = f"{self.api_url}/space/{self.space_id}/issue/new"

        payload = {
            "username": self.username,
            "password": self.password,
            "issues": [{
                "title": card_data.get('title', ''),
                "detail": card_data.get('detail', ''),
                "type": card_data.get('type', 'Bug'),
                "fields": fields,
                "creator": card_data.get('creator', self.username),
                "comment": card_data.get('comment', '')
            }]
        }

        headers = {"Content-Type": "application/json"}

        logger.info(f"创建 iCafe 卡片: {card_data.get('title', '')}")
        logger.info(f"请求字段: {json.dumps(fields, ensure_ascii=False)}")

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def create_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建 iCafe 卡片

        如果包含自定义字段导致 "Field name or value is incorrect" 错误，
        自动回退到仅使用标准字段重试。

        Args:
            card_data: 卡片数据
                - title: 标题
                - detail: 详情（HTML格式）
                - type: 类型（Task/Bug等）
                - fields: 字段字典
                - creator: 创建人
                - comment: 评论

        Returns:
            创建结果字典
        """
        try:
            all_fields = card_data.get('fields', {})

            result = self._send_create_request(card_data, all_fields)
            logger.debug(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

            if result.get("status") == 200:
                logger.success(f"✅ iCafe 卡片创建成功: {card_data.get('title', '')}")
                return {
                    "success": True,
                    "message": "卡片创建成功",
                    "data": result
                }

            error_msg = result.get('message', '未知错误')

            # 如果是字段错误，用标准字段重试
            if 'field name or value is incorrect' in error_msg.lower():
                logger.warning(f"字段不匹配，回退到标准字段重试: {error_msg}")
                # 只保留 iCafe 标准字段
                standard_fields = {}
                for key in ('负责人', '流程状态', '优先级'):
                    if key in all_fields:
                        standard_fields[key] = all_fields[key]

                retry_result = self._send_create_request(card_data, standard_fields)

                if retry_result.get("status") == 200:
                    logger.success(f"✅ iCafe 卡片创建成功（使用标准字段）: {card_data.get('title', '')}")
                    return {
                        "success": True,
                        "message": "卡片创建成功（部分自定义字段不支持，已自动跳过）",
                        "data": retry_result
                    }
                else:
                    retry_error = retry_result.get('message', '未知错误')
                    logger.error(f"❌ iCafe 卡片创建失败（标准字段重试）: {retry_error}")
                    return {
                        "success": False,
                        "message": retry_error,
                        "data": retry_result
                    }

            logger.error(f"❌ iCafe 卡片创建失败: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "data": result
            }

        except requests.exceptions.Timeout:
            logger.error("iCafe API 请求超时")
            return {
                "success": False,
                "message": "请求超时"
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"iCafe API 连接错误: {e}")
            return {
                "success": False,
                "message": f"连接错误: {e}"
            }
        except Exception as e:
            logger.error(f"创建 iCafe 卡片失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {e}"
            }
    
    def generate_card_title(self, alert_data: Dict[str, Any]) -> str:
        """
        根据告警数据生成卡片标题
        
        Args:
            alert_data: 告警数据
                - ip: 节点IP
                - cluster_id: 集群ID（可选）
                - alert_type: 告警类型
        
        Returns:
            生成的标题
        """
        ip = alert_data.get('ip', '')
        cluster_id = alert_data.get('cluster_id', '')
        alert_type = alert_data.get('alert_type', '')
        
        # 基础前缀
        prefix = "【长安LCC】【C3】【硬件维修】"
        
        # 根据是否有集群ID生成不同格式
        if cluster_id and cluster_id.strip():
            # 有集群ID: 集群ID+"集群"+IP+"节点"+告警类型
            title = f"{prefix} {cluster_id}集群{ip}节点{alert_type}"
        else:
            # 无集群ID: IP+"节点"+告警类型
            title = f"{prefix} {ip}节点{alert_type}"
        
        return title
    
    def generate_card_detail(self, alert_data: Dict[str, Any], diagnosis_data: Optional[Dict[str, Any]] = None) -> str:
        """
        根据告警数据生成卡片详情（HTML格式）
        
        Args:
            alert_data: 告警数据
            diagnosis_data: 诊断数据（可选）
        
        Returns:
            HTML格式的详情内容
        """
        html_parts = []
        
        # 告警基本信息
        html_parts.append("<h3>告警信息</h3>")
        html_parts.append("<ul>")
        html_parts.append(f"<li><strong>告警类型</strong>: {alert_data.get('alert_type', '')}</li>")
        html_parts.append(f"<li><strong>组件</strong>: {alert_data.get('component', '')}</li>")
        html_parts.append(f"<li><strong>严重程度</strong>: {alert_data.get('severity', '')}</li>")
        html_parts.append(f"<li><strong>节点IP</strong>: {alert_data.get('ip', '')}</li>")
        if alert_data.get('cluster_id'):
            html_parts.append(f"<li><strong>集群ID</strong>: {alert_data.get('cluster_id', '')}</li>")
        if alert_data.get('hostname'):
            html_parts.append(f"<li><strong>主机名</strong>: {alert_data.get('hostname', '')}</li>")
        html_parts.append(f"<li><strong>发生时间</strong>: {alert_data.get('timestamp', '')}</li>")
        html_parts.append("</ul>")
        
        # 诊断信息（如果有）
        if diagnosis_data:
            html_parts.append("<h3>诊断信息</h3>")
            if diagnosis_data.get('manual_matched') and diagnosis_data.get('manual_solution'):
                html_parts.append("<h4>故障手册匹配</h4>")
                html_parts.append(f"<p>{diagnosis_data.get('manual_solution', '')}</p>")
            
            if diagnosis_data.get('ai_interpretation'):
                html_parts.append("<h4>AI 分析</h4>")
                html_parts.append(f"<div>{diagnosis_data.get('ai_interpretation', '')}</div>")
        
        # 原始数据链接
        html_parts.append("<h3>相关链接</h3>")
        html_parts.append(f"<p><a href='#'>告警详情页面</a></p>")
        
        return "\n".join(html_parts)
    
    def build_card_fields(self, form_data: Dict[str, Any], card_type: str = 'Bug') -> Dict[str, Any]:
        """
        构建卡片字段（支持 Bug 和 Task 类型）

        Args:
            form_data: 表单数据
                - responsible_person: 负责人
                - subcategory: 细分分类
                - work_hours: 工时
                - plan: 所属计划
                - direction: 方向大类（Task类型）
                - category: 汇总分类（Task类型）
            card_type: 卡片类型，'Bug' 或 'Task'

        Returns:
            字段字典
        """
        fields = {}

        # 标准字段（所有类型通用）
        if form_data.get('responsible_person'):
            fields['负责人'] = form_data['responsible_person']

        fields['流程状态'] = '新建'

        if card_type == 'Task':
            # Task 类型字段
            # 必填字段：方向大类、汇总分类、细分分类
            fields['方向大类'] = form_data.get('direction', '硬件')
            fields['汇总分类'] = form_data.get('category', '运维事件')
            fields['细分分类'] = form_data.get('subcategory', 'GPU')

            # 可选字段
            if form_data.get('work_hours'):
                fields['占用工时'] = str(form_data['work_hours'])

            if form_data.get('plan'):
                fields['所属计划'] = form_data['plan']

        else:
            # Bug 类型字段
            fields['优先级'] = 'P1-High'

            # 用户填写的自定义字段
            if form_data.get('subcategory'):
                fields['细分分类'] = form_data['subcategory']

            if form_data.get('work_hours'):
                fields['占用工时'] = str(form_data['work_hours'])

            if form_data.get('plan'):
                fields['所属计划'] = form_data['plan']

            # 固定业务字段
            fields['有感事件'] = '否'
            fields['TAM负责人'] = '陈少禄'
            fields['汇总分类'] = '运维事件'
            fields['方向大类'] = '计算'

        return fields


def get_icafe_service(config: Dict[str, Any]) -> ICafeService:
    """
    获取 iCafe 服务实例
    
    Args:
        config: iCafe 配置
    
    Returns:
        ICafeService 实例
    """
    return ICafeService(config)