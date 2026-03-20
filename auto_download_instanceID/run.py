#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
from datetime import datetime, timedelta
from bcc_downloader import BCCDownloader, CCEDownloader
from config import COOKIES, REGION, DB_CONFIG, CONTAINER_DB_CONFIG
from database_writer import InstanceDatabaseWriter

def get_week_start():
    """获取本周一的日期"""
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.strftime('%Y-%m-%d')

def check_weekly_file_exists():
    """检查本周是否已有CSV文件"""
    # 获取本周一的日期范围（只比较日期，不比较时间）
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # 获取所有CSV文件（在 bcc_csv 目录下）
    csv_files = glob.glob("bcc_csv/bcc_instances_*.csv")
    
    for file in csv_files:
        try:
            # 从文件名提取时间戳
            timestamp_str = file.split('_')[2].split('.')[0]
            timestamp = int(timestamp_str)
            file_date = datetime.fromtimestamp(timestamp).date()
            
            # 检查文件是否在本周内
            if monday <= file_date <= sunday:
                print(f"发现本周文件: {file} (创建于 {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
                return True
        except (ValueError, IndexError):
            continue
    
    return False

def check_weekly_cce_file_exists(cluster_id):
    """检查本周是否已有CCE节点CSV文件"""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    
    # 在 cce_csv 目录下查找
    csv_files = glob.glob(f"cce_csv/cce_nodes_{cluster_id}_*.csv")
    
    for file in csv_files:
        try:
            # 从文件名提取时间戳
            timestamp_str = file.split('_')[-1].split('.')[0]
            timestamp = int(timestamp_str)
            file_date = datetime.fromtimestamp(timestamp).date()
            
            if monday <= file_date <= sunday:
                print(f"发现本周CCE节点文件: {file} (创建于 {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')})")
                return True
        except (ValueError, IndexError):
            continue
    
    return False


def main():
    # 初始化数据库写入器（宿主机）
    try:
        db_writer = InstanceDatabaseWriter(**DB_CONFIG)
        enable_db = True
        print("✓ 数据库自动入库功能已启用（宿主机）")
    except Exception as e:
        print(f"⚠ 数据库配置错误，将跳过自动入库: {e}")
        enable_db = False

    # 初始化容器数据库写入器
    try:
        container_writer = InstanceDatabaseWriter(**CONTAINER_DB_CONFIG)
        enable_container_db = True
        print("✓ 容器数据库同步功能已启用")
    except Exception as e:
        print(f"⚠ 容器数据库配置错误，将跳过同步: {e}")
        enable_container_db = False
    
    # BCC 下载
    if check_weekly_file_exists():
        print("本周已有BCC CSV文件，跳过下载")
    else:
        downloader = BCCDownloader(COOKIES, region=REGION)
        
        print("正在下载BCC实例数据...")
        result = downloader.download_instances()
        
        if result['success']:
            print(f"下载成功! 状态码: {result['status_code']}")
            
            format_type = result.get('format', 'json')
            print(f"数据格式: {format_type}")
            
            filename = downloader.save_to_file(result['data'], format_type=format_type)
            print(f"数据已保存到: {filename}")
            
            if format_type == 'csv':
                lines = result['data'].strip().split('\n')
                print(f"共获取到 {len(lines)-1} 个实例（不包括表头）")
            elif isinstance(result['data'], dict) and 'result' in result['data']:
                instances = result['data']['result']
                print(f"共获取到 {len(instances)} 个实例")
            
            # 自动入库（宿主机）
            if enable_db and format_type == 'csv':
                try:
                    db_writer.import_csv_to_db(filename, source_type='BCC')
                except Exception as e:
                    print(f"⚠ BCC数据入库失败: {e}")
            # 同步到容器数据库
            if enable_container_db and format_type == 'csv':
                try:
                    container_writer.import_csv_to_db(filename, source_type='BCC')
                    print(f"✓ BCC数据已同步到容器数据库")
                except Exception as e:
                    print(f"⚠ BCC数据同步到容器失败: {e}")
        else:
            print(f"下载失败: {result['error']}")
            if result['status_code']:
                print(f"状态码: {result['status_code']}")
            if 'raw_response' in result:
                print(f"原始响应: {result['raw_response']}")
    
    # CCE 节点下载（支持多集群）
    clusters = []
    
    # 从 config 读取 CLUSTER_IDS（list/tuple 或 逗号分隔字符串）
    try:
        from config import CLUSTER_IDS as _CIDS
        if isinstance(_CIDS, (list, tuple)):
            clusters.extend([str(x).strip() for x in _CIDS if str(x).strip()])
        elif isinstance(_CIDS, str):
            clusters.extend([x.strip() for x in _CIDS.split(',') if x.strip()])
    except Exception:
        pass
    
    # 从 config 读取单个 CLUSTER_ID
    try:
        from config import CLUSTER_ID as _CID
        if _CID:
            clusters.append(str(_CID).strip())
    except Exception:
        pass
    
    # 从环境变量读取（支持多个或单个）
    env_ids = os.getenv('CCE_CLUSTER_IDS')
    if env_ids:
        clusters.extend([x.strip() for x in env_ids.split(',') if x.strip()])
    else:
        env_id = os.getenv('CCE_CLUSTER_ID')
        if env_id:
            clusters.append(env_id.strip())
    
    # 去重并保持顺序
    seen = set()
    clusters = [c for c in clusters if not (c in seen or seen.add(c))]
    
    if not clusters:
        print("未配置集群ID（config.CLUSTER_IDS/CLUSTER_ID 或环境变量 CCE_CLUSTER_IDS/CCE_CLUSTER_ID），跳过CCE节点下载。")
    else:
        for cluster_id in clusters:
            if check_weekly_cce_file_exists(cluster_id):
                print(f"本周已有CCE节点CSV文件，集群 {cluster_id} 跳过下载")
                continue
            cce = CCEDownloader(COOKIES, region=REGION)
            print(f"正在下载CCE集群({cluster_id})节点列表...")
            cce_result = cce.download_nodes(cluster_id)
            
            if cce_result['success']:
                print(f"CCE下载成功! 状态码: {cce_result['status_code']}")
                cce_format = cce_result.get('format', 'csv')
                print(f"CCE数据格式: {cce_format}")
                
                cce_filename = cce.save_to_file(cce_result['data'], cluster_id, format_type=cce_format)
                print(f"CCE节点数据已保存到: {cce_filename}")
                
                if cce_format == 'csv':
                    lines = cce_result['data'].strip().split('\n')
                    print(f"共获取到 {len(lines)-1} 个节点（不包括表头）")
                
                # 自动入库（宿主机）
                if enable_db and cce_format == 'csv':
                    try:
                        db_writer.import_csv_to_db(cce_filename, source_type='CCE', cluster_id=cluster_id)
                    except Exception as e:
                        print(f"⚠ CCE数据入库失败 [{cluster_id}]: {e}")
                # 同步到容器数据库
                if enable_container_db and cce_format == 'csv':
                    try:
                        container_writer.import_csv_to_db(cce_filename, source_type='CCE', cluster_id=cluster_id)
                        print(f"✓ CCE数据已同步到容器数据库 [{cluster_id}]")
                    except Exception as e:
                        print(f"⚠ CCE数据同步到容器失败 [{cluster_id}]: {e}")
            else:
                print(f"CCE下载失败: {cce_result['error']}")
                if cce_result.get('status_code'):
                    print(f"状态码: {cce_result['status_code']}")
                if 'raw_response' in cce_result:
                    print(f"原始响应: {cce_result['raw_response']}")
    
    
if __name__ == "__main__":
    main()
