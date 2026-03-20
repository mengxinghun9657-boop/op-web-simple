#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BCC/CCE实例数据库写入器
将CSV数据自动解析并写入MySQL数据库，支持自动覆盖
"""

import csv
import pymysql
import glob
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class InstanceDatabaseWriter:
    def __init__(self, host='127.0.0.1', port=8306, user='root', 
                 password='DF210354ws!', database='mydb', 
                 bcc_table='bce_bcc_instances', cce_table='bce_cce_nodes'):
        """
        初始化数据库写入器
        
        Args:
            host: 数据库主机
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            database: 数据库名
            bcc_table: BCC实例表名
            cce_table: CCE节点表名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.bcc_table = bcc_table
        self.cce_table = cce_table
    
    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4'
        )
    
    def clean_field_name(self, name):
        """清理字段名，转换为合法的MySQL字段名"""
        return (name.replace(" ", "_")
                   .replace("%", "percent")
                   .replace("/", "_")
                   .replace("(", "")
                   .replace(")", "")
                   .replace("-", "_")
                   .lower())
    
    def infer_mysql_type(self, value):
        """根据值推断MySQL数据类型"""
        if value is None or value == '':
            return "TEXT"  # 默认使用TEXT以防止截断
        
        # 尝试转换为数值
        try:
            if '.' in str(value):
                float(value)
                return "DECIMAL(20,2)"
            else:
                int(value)
                return "INT"
        except (ValueError, TypeError):
            pass
        
        # 字符串类型 - 使用更宽松的长度限制
        value_str = str(value)
        if len(value_str) <= 50:
            return "VARCHAR(100)"  # 留余空间
        elif len(value_str) <= 255:
            return "VARCHAR(500)"  # 留余空间
        else:
            return "TEXT"  # 长文本使用TEXT
    
    def create_table_from_csv_header(self, csv_file_path, source_type='BCC'):
        """
        根据CSV表头创建数据库表（如果不存在）
        
        Args:
            csv_file_path: CSV文件路径
            source_type: 数据源类型（BCC 或 CCE）
        """
        # 根据数据类型选择表名
        table_name = self.bcc_table if source_type == 'BCC' else self.cce_table
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查表是否存在
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if cursor.fetchone():
                print(f"✓ 表 `{table_name}` 已存在")
                return True
            
            # 读取CSV表头
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                
                # 扫描前100行数据用于类型推断（而不是只看第一行）
                sample_rows = []
                for i, row in enumerate(reader):
                    sample_rows.append(row)
                    if i >= 99:  # 最多扫描100行
                        break
            
            if not headers:
                print(f"✗ CSV文件无表头: {csv_file_path}")
                return False
            
            # 清理字段名
            original_fields = list(headers)
            cleaned_fields = [self.clean_field_name(f) for f in original_fields]
            
            # 基础字段（根据数据类型调整）
            if source_type == 'BCC':
                base_fields = ["id", "collect_date", "insert_time"]
                base_types = ["BIGINT AUTO_INCREMENT", "DATE", "DATETIME"]
            else:  # CCE
                base_fields = ["id", "cluster_id", "collect_date", "insert_time"]
                base_types = ["BIGINT AUTO_INCREMENT", "VARCHAR(100)", "DATE", "DATETIME"]
            
            # 数据字段类型推断（基于多行样本）
            data_types = []
            if sample_rows:
                for orig_field in original_fields:
                    # 收集该字段所有样本值
                    field_values = [row.get(orig_field, '') for row in sample_rows]
                    # 找出最长的值来推断类型
                    max_length_value = max(field_values, key=lambda x: len(str(x)) if x else 0)
                    mysql_type = self.infer_mysql_type(max_length_value)
                    data_types.append(mysql_type)
            else:
                data_types = ["TEXT"] * len(original_fields)  # 默认使用TEXT
            
            # 组装建表语句
            all_fields = base_fields + cleaned_fields
            all_types = base_types + data_types
            
            col_defs = ', '.join([f"`{f}` {t}" for f, t in zip(all_fields, all_types)])
            
            # 根据数据类型设置不同的唯一键
            if source_type == 'BCC':
                # BCC使用实例ID作为唯一标识（假设第一个字段是BCC_ID）
                first_field = cleaned_fields[0] if cleaned_fields else 'id'
                unique_key = f"UNIQUE KEY `uk_bcc_id` (`{first_field}`)"
            else:  # CCE
                # CCE使用集群ID+实例ID作为唯一标识（第二个字段通常是实例名称/ID）
                if len(cleaned_fields) >= 2:
                    instance_field = cleaned_fields[1]  # 实例名称/ID
                    unique_key = f"UNIQUE KEY `uk_cluster_instance` (`cluster_id`, `{instance_field}`)"
                else:
                    # 降级方案：使用集群ID+日期
                    unique_key = "UNIQUE KEY `uk_cluster_date` (`cluster_id`, `collect_date`)"
            
            create_sql = f"""CREATE TABLE `{table_name}` (
                {col_defs},
                PRIMARY KEY (`id`),
                {unique_key}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
            
            cursor.execute(create_sql)
            conn.commit()
            print(f"✓ 成功创建表 `{table_name}`")
            return True
            
        except Exception as e:
            print(f"✗ 创建表失败: {e}")
            return False
        finally:
            conn.close()
    
    def convert_value(self, value):
        """转换值为合适的数据库类型"""
        if value is None or value == '':
            return None
        
        value_str = str(value).strip()
        if value_str.upper() in ('N/A', 'NULL', '-'):
            return None
        
        # 尝试转换为数值
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except (ValueError, TypeError):
            return value_str
    
    def extract_date_from_filename(self, csv_file_path):
        """从文件名中提取时间戳并转换为日期"""
        try:
            basename = os.path.basename(csv_file_path)
            # BCC文件名格式: bcc_instances_{timestamp}.csv
            # CCE文件名格式: cce_nodes_{cluster_id}_{timestamp}.csv
            parts = basename.replace('.csv', '').split('_')
            timestamp_str = parts[-1]  # 最后一部分是时间戳
            timestamp = int(timestamp_str)
            return datetime.fromtimestamp(timestamp).date()
        except (ValueError, IndexError) as e:
            print(f"⚠ 无法从文件名提取日期，使用当前日期: {e}")
            return datetime.now().date()
    
    def import_csv_to_db(self, csv_file_path, source_type='BCC', cluster_id=''):
        """
        导入CSV文件到数据库
        
        Args:
            csv_file_path: CSV文件路径
            source_type: 数据源类型（BCC 或 CCE）
            cluster_id: 集群ID（CCE数据需要）
        """
        if not os.path.exists(csv_file_path):
            print(f"✗ 文件不存在: {csv_file_path}")
            return False
        
        # 创建表（如果不存在）
        if not self.create_table_from_csv_header(csv_file_path, source_type):
            return False
        
        # 根据数据类型选择表名
        table_name = self.bcc_table if source_type == 'BCC' else self.cce_table
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 读取CSV
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                cleaned_headers = [self.clean_field_name(h) for h in headers]
                
                # 准备SQL（根据数据类型调整）
                if source_type == 'BCC':
                    all_fields = ["collect_date", "insert_time"] + cleaned_headers
                else:  # CCE
                    all_fields = ["cluster_id", "collect_date", "insert_time"] + cleaned_headers
                
                insert_fields = ', '.join([f"`{f}`" for f in all_fields])
                placeholders = ', '.join(['%s'] * len(all_fields))
                # 构建 UPDATE 字段列表：所有业务字段 + collect_date + insert_time
                update_fields = ', '.join([f"`{f}`=VALUES(`{f}`)" for f in cleaned_headers])
                update_fields += ", `collect_date`=VALUES(`collect_date`), `insert_time`=VALUES(`insert_time`)"
                
                insert_sql = f"""INSERT INTO `{table_name}` ({insert_fields}) 
                               VALUES ({placeholders})
                               ON DUPLICATE KEY UPDATE {update_fields}"""
                
                # 从文件名中提取采集日期
                collect_date = self.extract_date_from_filename(csv_file_path)
                insert_time = datetime.now()
                insert_values = []
                
                for row in reader:
                    # 基础字段（根据数据类型调整）
                    if source_type == 'BCC':
                        row_data = [collect_date, insert_time]
                    else:  # CCE
                        row_data = [cluster_id, collect_date, insert_time]
                    
                    # 数据字段
                    for orig_field in headers:
                        value = row.get(orig_field, '')
                        converted_value = self.convert_value(value)
                        row_data.append(converted_value)
                    
                    insert_values.append(row_data)
            
            # 批量插入
            if insert_values:
                cursor.executemany(insert_sql, insert_values)
                conn.commit()
                print(f"✓ 成功写入/更新 {len(insert_values)} 条记录 [{source_type}] {os.path.basename(csv_file_path)} (采集日期: {collect_date})")
                return True
            else:
                print(f"✗ 文件无有效数据: {csv_file_path}")
                return False
            
        except Exception as e:
            print(f"✗ 导入失败 {csv_file_path}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def import_latest_bcc_csv(self, bcc_dir='bcc_csv'):
        """导入最新的BCC CSV文件"""
        pattern = os.path.join(bcc_dir, "bcc_instances_*.csv")
        files = glob.glob(pattern)
        if not files:
            print(f"✗ 未找到BCC CSV文件: {pattern}")
            return False
        
        # 按修改时间排序，取最新的
        latest_file = max(files, key=os.path.getmtime)
        print(f"导入最新BCC文件: {latest_file}")
        return self.import_csv_to_db(latest_file, source_type='BCC')
    
    def import_latest_cce_csvs(self, cce_dir='cce_csv'):
        """导入所有最新的CCE CSV文件"""
        pattern = os.path.join(cce_dir, "cce_nodes_*.csv")
        files = glob.glob(pattern)
        if not files:
            print(f"✗ 未找到CCE CSV文件: {pattern}")
            return False
        
        # 按集群分组
        cluster_files = {}
        for file in files:
            basename = os.path.basename(file)
            # 文件名格式: cce_nodes_{cluster_id}_{timestamp}.csv
            parts = basename.replace('cce_nodes_', '').replace('.csv', '').rsplit('_', 1)
            if len(parts) == 2:
                cluster_id, timestamp = parts
                if cluster_id not in cluster_files:
                    cluster_files[cluster_id] = []
                cluster_files[cluster_id].append((file, int(timestamp)))
        
        # 每个集群取最新文件
        success_count = 0
        for cluster_id, file_list in cluster_files.items():
            latest_file = max(file_list, key=lambda x: x[1])[0]
            print(f"导入集群 {cluster_id} 最新文件: {latest_file}")
            if self.import_csv_to_db(latest_file, source_type='CCE', cluster_id=cluster_id):
                success_count += 1
        
        print(f"✓ 成功导入 {success_count}/{len(cluster_files)} 个CCE集群数据")
        return success_count > 0
    
    def import_all_latest(self):
        """导入所有最新的BCC和CCE数据"""
        print("=" * 60)
        print("开始导入数据到数据库...")
        print("=" * 60)
        
        bcc_success = self.import_latest_bcc_csv()
        cce_success = self.import_latest_cce_csvs()
        
        print("=" * 60)
        if bcc_success or cce_success:
            print("✓ 数据导入完成")
        else:
            print("✗ 数据导入失败")
        print("=" * 60)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BCC/CCE实例数据库导入工具')
    parser.add_argument('--host', default='127.0.0.1', help='数据库主机')
    parser.add_argument('--port', type=int, default=8306, help='数据库端口')
    parser.add_argument('--user', default='root', help='数据库用户名')
    parser.add_argument('--password', default='DF210354ws!', help='数据库密码')
    parser.add_argument('--database', default='mydb', help='数据库名')
    parser.add_argument('--bcc-table', default='bce_bcc_instances', help='BCC表名')
    parser.add_argument('--cce-table', default='bce_cce_nodes', help='CCE表名')
    
    args = parser.parse_args()
    
    writer = InstanceDatabaseWriter(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        bcc_table=args.bcc_table,
        cce_table=args.cce_table
    )
    
    writer.import_all_latest()


if __name__ == "__main__":
    main()
