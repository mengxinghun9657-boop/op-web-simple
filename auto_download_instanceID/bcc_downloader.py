#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import os
from urllib.parse import urlencode

class BCCDownloader:
    def __init__(self, cookies, region='cd'):
        self.base_url = "https://console.bce.baidu.com/api/bcc/instance/download"
        self.region = region
        self.session = requests.Session()
        
        # 设置cookies
        if isinstance(cookies, str):
            self._parse_cookies(cookies)
        else:
            self.session.cookies.update(cookies)
        
        # 从cookie中提取CSRF token
        csrf_token = self._extract_csrf_token()
        
        # 基础headers
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'csrftoken': csrf_token,
            'referer': 'https://console.bce.baidu.com/bcc/',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'x-region': region,
            'x-request-by': 'RestClient'
        }
    
    def _parse_cookies(self, cookie_string):
        """解析cookie字符串"""
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session.cookies.set(name, value)
    
    def _extract_csrf_token(self):
        """从cookie中提取CSRF token"""
        bce_user_info = self.session.cookies.get('bce-user-info')
        if bce_user_info:
            # 去掉引号
            return bce_user_info.strip('"')
        return None
    
    def download_instances(self, **kwargs):
        """下载BCC实例数据"""
        
        # 默认参数
        params = {
            'keywordType': kwargs.get('keyword_type', 'fuzzySearch'),
            'order': kwargs.get('order', 'desc'),
            'orderBy': kwargs.get('order_by', 'createTime'),
            'serverType': kwargs.get('server_type', 'BCC'),
            'enableBid': kwargs.get('enable_bid', True),
            'filters': json.dumps(kwargs.get('filters', [])),
            'needAlarmStatus': kwargs.get('need_alarm_status', True),
            'isAdvancedSearch': kwargs.get('is_advanced_search', False),
            'region': self.region,
            'locale': kwargs.get('locale', 'zh-cn'),
            '_': str(int(time.time() * 1000))  # 时间戳
        }
        
        # 构建完整URL
        url = f"{self.base_url}?{urlencode(params)}"
        
        try:
            response = self.session.post(url, headers=self.headers, json={})
            response.raise_for_status()
            
            # 处理UTF-8 BOM
            text = response.text
            if text.startswith('\ufeff'):
                text = text[1:]
            
            # 检查响应内容
            if not text.strip():
                return {
                    'success': False,
                    'error': '响应内容为空',
                    'status_code': response.status_code,
                    'raw_response': text
                }
            
            # 检查是否为CSV格式（根据内容判断）
            if text.startswith('BCC_ID,') or (',' in text and '\n' in text and len(text.split('\n')) > 1):
                return {
                    'success': True,
                    'data': text,
                    'format': 'csv',
                    'status_code': response.status_code
                }
            
            # 尝试解析JSON
            try:
                data = json.loads(text)
                return {
                    'success': True,
                    'data': data,
                    'format': 'json',
                    'status_code': response.status_code
                }
            except json.JSONDecodeError:

                
                return {
                    'success': False,
                    'error': '响应不是有效的JSON或CSV格式',
                    'status_code': response.status_code,
                    'raw_response': text[:500]
                }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def save_to_file(self, data, filename=None, format_type='json'):
        """保存数据到文件"""
        if filename is None:
            ext = 'csv' if format_type == 'csv' else 'json'
            filename = f"bcc_instances_{int(time.time())}.{ext}"
        
        # 确保目录存在
        directory = os.path.dirname(filename) or 'bcc_csv'
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        full_path = filename if os.path.isabs(filename) else os.path.join(directory, os.path.basename(filename))
        
        with open(full_path, 'w', encoding='utf-8') as f:
            if format_type == 'csv' or isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return full_path

class CCEDownloader:
    def __init__(self, cookies, region='cd'):
        self.base_url_base = "https://console.bce.baidu.com/api/cce/service/v2/cluster"
        self.region = region
        self.session = requests.Session()
        
        # 设置cookies
        if isinstance(cookies, str):
            self._parse_cookies(cookies)
        else:
            self.session.cookies.update(cookies)
        
        # 从cookie中提取CSRF token
        csrf_token = self._extract_csrf_token()
        
        # 基础headers
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'csrftoken': csrf_token,
            'referer': 'https://console.bce.baidu.com/cce/',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'x-region': region,
            'x-request-by': 'RestClient'
        }
    
    def _parse_cookies(self, cookie_string):
        """解析cookie字符串"""
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                self.session.cookies.set(name, value)
    
    def _extract_csrf_token(self):
        """从cookie中提取CSRF token"""
        bce_user_info = self.session.cookies.get('bce-user-info')
        if bce_user_info:
            # 去掉引号
            return bce_user_info.strip('"')
        return None
    
    def download_nodes(self, cluster_id, **kwargs):
        """下载CCE集群的节点列表（模拟控制台真实请求）"""
        
        # query 参数
        params = {
            'locale': kwargs.get('locale', 'zh-cn'),
            '_': str(int(time.time() * 1000))
        }
        
        url = f"{self.base_url_base}/{cluster_id}/instances/download?{urlencode(params)}"
        
        # 请求体：尽量还原浏览器请求
        payload = {
            "cceInstanceIDs": kwargs.get('cceInstanceIDs', []),
            "exportAll": kwargs.get('exportAll', True),
            "calculateGPUCountRequested": kwargs.get('calculateGPUCountRequested', False),
            "keywordType": kwargs.get('keywordType', 'k8sNodeName'),
            "clusterUuid": cluster_id,
            "clusterRole": kwargs.get('clusterRole', 'node'),
            "orderBy": kwargs.get('orderBy', 'createdAt'),
            "order": kwargs.get('order', 'desc'),
        }
        
        try:
            response = self.session.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            # CCE 导出接口返回的是二进制流/CSV附件，content-type 为 application/octet-stream
            content_type = response.headers.get('Content-Type', '')
            text = response.text
            if text.startswith('\ufeff'):
                text = text[1:]
            
            if not text.strip():
                return {
                    'success': False,
                    'error': '响应内容为空',
                    'status_code': response.status_code,
                    'raw_response': text
                }
            
            # 如果是 CSV（即使 header 是 octet-stream，我们用内容判断）
            if (',' in text and '\n' in text and len(text.split('\n')) > 1):
                return {
                    'success': True,
                    'data': text,
                    'format': 'csv',
                    'status_code': response.status_code,
                    'content_type': content_type
                }
            
            # 尝试解析 JSON，看是否为错误信息
            try:
                data = json.loads(text)
                # 这里不直接认为成功，交给上层决定
                return {
                    'success': False,
                    'data': data,
                    'format': 'json',
                    'status_code': response.status_code,
                    'error': '接口返回JSON而非CSV，可能为错误或空数据',
                    'raw_response': text[:500]
                }
            except json.JSONDecodeError:
                return {
                    'success': False,
                    'error': '响应不是有效的JSON或CSV格式',
                    'status_code': response.status_code,
                    'raw_response': text[:500]
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def save_to_file(self, data, cluster_id, filename=None, format_type='csv'):
        """保存CCE节点数据到文件"""
        if filename is None:
            ext = 'csv' if format_type == 'csv' or isinstance(data, str) else 'json'
            filename = f"cce_nodes_{cluster_id}_{int(time.time())}.{ext}"
        
        directory = os.path.dirname(filename) or 'cce_csv'
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        full_path = filename if os.path.isabs(filename) else os.path.join(directory, os.path.basename(filename))
        
        with open(full_path, 'w', encoding='utf-8') as f:
            if format_type == 'csv' or isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return full_path


def main():
    from config import COOKIES, REGION
    
    # 创建下载器实例
    downloader = BCCDownloader(COOKIES, region=REGION)
    
    # 下载数据
    print("正在下载BCC实例数据...")
    result = downloader.download_instances()
    
    if result['success']:
        print(f"下载成功! 状态码: {result['status_code']}")
        
        # 保存到文件
        filename = downloader.save_to_file(result['data'])
        print(f"数据已保存到: {filename}")
        
        # 显示部分数据
        if 'result' in result['data']:
            instances = result['data']['result']
            print(f"共获取到 {len(instances)} 个实例")
    else:
        print(f"下载失败: {result['error']}")
        if result['status_code']:
            print(f"状态码: {result['status_code']}")

if __name__ == "__main__":
    main()
