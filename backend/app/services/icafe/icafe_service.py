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
            # 构造测试URL - 使用简单的API端点
            test_url = f"{self.api_url}/space/{self.space_id}/info"
            
            # 测试请求 - 使用较短的超时时间
            headers = {"Content-Type": "application/json"}
            
            logger.info(f"测试 iCafe 连接: {test_url}")
            
            response = requests.get(
                test_url, 
                headers=headers, 
                timeout=10,  # 10秒超时
                auth=(self.username, self.password) if self.username and self.password else None
            )
            
            # 检查响应状态
            if response.status_code == 200:
                logger.success("✅ iCafe 连接测试成功")
                return True, "连接测试成功"
            elif response.status_code == 401:
                logger.warning("❌ iCafe 认证失败")
                return False, "认证失败：用户名或密码错误"
            elif response.status_code == 404:
                logger.warning("❌ iCafe 空间不存在")
                return False, f"空间 {self.space_id} 不存在"
            else:
                logger.warning(f"❌ iCafe 连接失败: HTTP {response.status_code}")
                return False, f"连接失败：HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            logger.error("❌ iCafe 连接超时")
            return False, "连接超时：请检查网络连接和API地址"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ iCafe 连接错误: {e}")
            return False, f"连接错误：无法访问 {self.api_url}"
        except Exception as e:
            logger.error(f"❌ iCafe 连接测试失败: {e}")
            return False, f"测试失败：{str(e)}"

    def create_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建 iCafe 卡片
        
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
            url = f"{self.api_url}/space/{self.space_id}/issue/new"
            
            payload = {
                "username": self.username,
                "password": self.password,
                "issues": [{
                    "title": card_data.get('title', ''),
                    "detail": card_data.get('detail', ''),
                    "type": card_data.get('type', 'Task'),
                    "fields": card_data.get('fields', {}),
                    "creator": card_data.get('creator', self.username),
                    "comment": card_data.get('comment', '')
                }]
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            logger.info(f"创建 iCafe 卡片: {card_data.get('title', '')}")
            logger.debug(f"请求 URL: {url}")
            logger.debug(f"请求 payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"响应结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
            if result.get("status") == 200:
                logger.success(f"✅ iCafe 卡片创建成功: {card_data.get('title', '')}")
                return {
                    "success": True,
                    "message": "卡片创建成功",
                    "data": result
                }
            else:
                error_msg = result.get('message', '未知错误')
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
    
    def build_card_fields(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建卡片字段（基于 HMLCC-2136 的字段结构）
        
        Args:
            form_data: 表单数据
                - responsible_person: 负责人
                - subcategory: 细分分类
                - work_hours: 工时
                - plan: 所属计划
        
        Returns:
            字段字典
        """
        fields = {}
        
        # 手动填写字段
        if form_data.get('responsible_person'):
            fields['负责人'] = form_data['responsible_person']
        
        if form_data.get('subcategory'):
            # 细分分类：BCC,GPU 格式
            fields['细分分类'] = form_data['subcategory']
        
        if form_data.get('work_hours'):
            fields['占用工时'] = str(form_data['work_hours'])
        
        # 下拉选择字段
        if form_data.get('plan'):
            fields['所属计划'] = form_data['plan']
        
        # 固定字段（基于 HMLCC-2136 的字段）
        fields['有感事件'] = '否'
        fields['TAM负责人'] = '陈少禄'
        fields['汇总分类'] = '运维事件'
        fields['方向大类'] = '计算'  # 从 HMLCC-2136 复制
        
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