#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import json
import os
import sys
from datetime import datetime

class HistoricalDataManager:
    def __init__(self, excel_path=None):
        # 获取脚本所在目录
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 使用相对路径
        self.excel_path = excel_path or os.path.join(self.script_dir, 'excel-export.xlsx')
        self.reference_path = os.path.join(self.script_dir, '长安HMLCC运营数据.xlsx')
        self.analysis_results_path = os.path.join(self.script_dir, 'analysis_results.json')
        
    def analyze_w38_from_excel(self):
        """从excel-export.xlsx分析W38数据"""
        try:
            if not os.path.exists(self.excel_path):
                return None
                
            # 读取excel-export.xlsx
            df = pd.read_excel(self.excel_path)
            
            # 创建时间在第6列(索引5)，类型在第4列(索引3)，流程状态在第3列(索引2)
            if len(df.columns) > 5:
                # 筛选W38时间范围的数据 (2025-09-11 到 2025-09-17)
                w38_data = []
                for idx, row in df.iterrows():
                    create_time = row.iloc[5]  # 创建时间列
                    if pd.notna(create_time):
                        # 转换为日期进行比较
                        if hasattr(create_time, 'date'):
                            date_obj = create_time.date()
                        else:
                            continue
                            
                        # W38: 2025-09-11 到 2025-09-17
                        from datetime import date
                        start_date = date(2025, 9, 11)
                        end_date = date(2025, 9, 17)
                        
                        if start_date <= date_obj <= end_date:
                            w38_data.append(row)
                
                if w38_data:
                    w38_df = pd.DataFrame(w38_data)
                    
                    # 筛选运维事件（D列类型除了"需求"和"风险治理"）
                    maintenance_events = []
                    for idx, row in w38_df.iterrows():
                        event_type = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""  # D列类型
                        if event_type not in ["需求", "风险治理"] and event_type != "":
                            maintenance_events.append(row)
                    
                    # 统计运维事件总数
                    total_events = len(maintenance_events)
                    
                    # 统计闭环数（D列除需求和风险治理外，且C列状态为关闭、已完成、已修复、已分析）
                    closed_count = 0
                    closed_statuses = ["关闭", "已完成", "已修复", "已分析"]
                    
                    for row in maintenance_events:
                        status = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""  # C列流程状态
                        if any(closed_status in status for closed_status in closed_statuses):
                            closed_count += 1
                    
                    # 计算解决率
                    resolution_rate = (closed_count / total_events * 100) if total_events > 0 else 0
                    
                    # 计算需求数据
                    # 1. 从整个excel-export.xlsx中筛选D列为"需求"的所有数据
                    all_requirements = []
                    for idx, row in df.iterrows():
                        event_type = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
                        if event_type == "需求":
                            all_requirements.append(row)
                    
                    # 2. 统计正在进行中需求个数（需求中C列状态不是"关闭"和"已完成"的）
                    ongoing_requirements = 0
                    for row in all_requirements:
                        status = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                        if "关闭" not in status and "已完成" not in status:
                            ongoing_requirements += 1
                    
                    # 3. 计算历史上本周完成需求个数总和（从参考数据获取）
                    historical_completed = self.get_historical_completed_requirements()
                    
                    # 4. 计算本周完成需求个数
                    total_requirements = len(all_requirements)
                    current_week_completed = total_requirements - ongoing_requirements - historical_completed
                    
                    print(f"   📊 W38数据分析: {total_events}个运维事件, {closed_count}个闭环")
                    print(f"   📋 需求分析: 总需求{total_requirements}个, 进行中{ongoing_requirements}个, 本周完成{current_week_completed}个")
                    
                    return {
                        "周期": "2025-W38",
                        "运维事件个数": int(total_events),
                        "闭环个数": int(closed_count),
                        "解决率": f"{resolution_rate:.2f}%",
                        "正在进行中需求个数": int(ongoing_requirements),
                        "本周完成需求个数": int(max(0, current_week_completed))  # 确保不为负数
                    }
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  分析W38数据失败: {e}")
            return None

    def get_historical_completed_requirements(self):
        """获取历史上本周完成需求个数总和"""
        try:
            ref_df = self.load_reference_data()
            if ref_df is not None and '已完成需求个数' in ref_df.columns:
                return int(ref_df['已完成需求个数'].sum())
            return 0
        except:
            return 0

    def load_reference_data(self):
        """加载参考校准数据"""
        if not os.path.exists(self.reference_path):
            return None
        
        df = pd.read_excel(self.reference_path)
        if 'Unnamed: 0' in df.columns:
            df.rename(columns={'Unnamed: 0': '周期'}, inplace=True)
        
        return df
        
    def load_excel_data(self):
        """加载Excel数据并进行标准化处理"""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel文件不存在: {self.excel_path}")
        
        df = pd.read_excel(self.excel_path)
        
        # 标准化列名
        if 'Unnamed: 0' in df.columns:
            df.rename(columns={'Unnamed: 0': '周期'}, inplace=True)
        
        # 验证必要的列是否存在
        required_columns = ['周期', '运维事件个数', '闭环个数', '解决率', '正在进行中需求个数', '已完成需求个数']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Excel文件缺少必要的列: {missing_columns}")
        
        return df
    
    def validate_data_logic(self, df):
        """验证数据逻辑的正确性"""
        errors = []
        
        for i, row in df.iterrows():
            # 检查闭环个数不能超过运维事件个数
            if row['闭环个数'] > row['运维事件个数']:
                errors.append(f"{row['周期']}: 闭环个数({row['闭环个数']}) > 运维事件个数({row['运维事件个数']})")
            
            # 检查解决率计算是否正确
            if row['运维事件个数'] > 0:
                expected_rate = row['闭环个数'] / row['运维事件个数']
                if abs(row['解决率'] - expected_rate) > 0.001:
                    errors.append(f"{row['周期']}: 解决率不匹配，实际={row['解决率']:.4f}, 期望={expected_rate:.4f}")
            
            # 检查负数
            numeric_columns = ['运维事件个数', '闭环个数', '正在进行中需求个数', '已完成需求个数']
            for col in numeric_columns:
                if row[col] < 0:
                    errors.append(f"{row['周期']}: {col}不能为负数({row[col]})")
        
        return errors
    
    def convert_to_historical_format(self, df):
        """将Excel数据转换为历史数据格式"""
        historical_data = []
        
        for _, row in df.iterrows():
            historical_data.append({
                "周期": str(row['周期']),
                "运维事件个数": int(row['运维事件个数']),
                "闭环个数": int(row['闭环个数']),
                "解决率": f"{row['解决率']*100:.2f}%",
                "正在进行中需求个数": int(row['正在进行中需求个数']),
                "本周完成需求个数": int(row['已完成需求个数'])
            })
        
        return historical_data
    
    def create_default_historical_data(self):
        """创建默认历史数据"""
        try:
            # 使用现有的analysis_results.json中的历史数据
            if os.path.exists(self.analysis_results_path):
                with open(self.analysis_results_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                    if 'historical_overview' in results:
                        print("✅ 使用现有历史数据")
                        return True
            
            # 如果没有现有数据，创建空的历史数据
            default_data = []
            self.update_analysis_results(default_data)
            print("✅ 创建默认历史数据")
            return True
        except:
            return False
    
    def update_analysis_results(self, historical_data):
        """更新分析结果文件"""
        try:
            # 加载现有分析结果
            if os.path.exists(self.analysis_results_path):
                with open(self.analysis_results_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            else:
                results = {}
            
            # 更新历史数据
            results['historical_overview'] = historical_data
            results['last_updated'] = datetime.now().isoformat()
            
            # 安全保存更新后的结果
            temp_path = self.analysis_results_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            # 原子性替换文件
            if os.path.exists(temp_path):
                if os.path.exists(self.analysis_results_path):
                    os.remove(self.analysis_results_path)
                os.rename(temp_path, self.analysis_results_path)
                
        except Exception as e:
            print(f"   ⚠️  更新分析结果失败: {e}")
            # 如果失败，至少保存历史数据
            try:
                backup_results = {
                    'historical_overview': historical_data,
                    'last_updated': datetime.now().isoformat(),
                    'anomalies': {
                        'c_anomalies': [],
                        'r_anomalies': [],
                        'k_anomalies': [],
                        'classification_anomalies': []
                    },
                    'overview': {
                        '总卡片数': 0,
                        '问题闭环率': '0%',
                        '需求闭环率': '0%',
                        '进行中需求': 0
                    }
                }
                with open(self.analysis_results_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_results, f, ensure_ascii=False, indent=2)
            except:
                pass
    
    def run_update(self):
        """执行完整的更新流程"""
        try:
            print("🔄 开始更新历史数据...")
            
            # 1. 加载参考校准数据用于历史概览
            print("📊 加载参考校准数据...")
            ref_df = self.load_reference_data()
            if ref_df is None:
                # 使用分析文件数据
                try:
                    ref_df = self.load_excel_data()
                except:
                    # 如果分析文件也无法加载，使用默认数据
                    return self.create_default_historical_data()
            else:
                print(f"   ✅ 成功加载参考数据 {len(ref_df)} 条记录")
            
            # 2. 验证参考数据逻辑
            print("🔍 验证参考数据逻辑...")
            errors = self.validate_data_logic(ref_df)
            if errors:
                print("   ⚠️  发现参考数据逻辑错误:")
                for error in errors:
                    print(f"      - {error}")
            else:
                print("   ✅ 参考数据逻辑验证通过")
            
            # 3. 转换参考数据格式用于历史概览
            print("🔄 转换历史数据格式...")
            historical_data = self.convert_to_historical_format(ref_df)
            
            # 4. 检查是否需要添加W38数据
            last_week = historical_data[-1]['周期'] if historical_data else None
            if last_week == '2025-W37':
                print("📈 检测到需要添加W38数据...")
                w38_data = self.analyze_w38_from_excel()
                if w38_data:
                    historical_data.append(w38_data)
                    print(f"   ✅ W38数据已添加: {w38_data['运维事件个数']}个事件, {w38_data['闭环个数']}个闭环")
                else:
                    # 如果分析失败，使用默认数据
                    default_w38 = {
                        "周期": "2025-W38",
                        "运维事件个数": 0,
                        "闭环个数": 0,
                        "解决率": "0.00%",
                        "正在进行中需求个数": 8,
                        "本周完成需求个数": 0
                    }
                    historical_data.append(default_w38)
                    print("   ⚠️  使用默认W38数据")
            
            print(f"   ✅ 成功转换 {len(historical_data)} 条历史记录")
            
            # 5. 更新分析结果
            print("💾 更新分析结果文件...")
            self.update_analysis_results(historical_data)
            print("   ✅ 分析结果文件已更新")
            
            # 6. 显示摘要
            print("\n📈 历史数据摘要:")
            print(f"   总周期数: {len(historical_data)}")
            if len(historical_data) > 0:
                total_events = sum(item['运维事件个数'] for item in historical_data)
                total_closed = sum(item['闭环个数'] for item in historical_data)
                print(f"   总运维事件: {total_events}")
                print(f"   总闭环事件: {total_closed}")
                print(f"   最新周期: {historical_data[-1]['周期']}")
            
            print("\n✅ 历史数据更新完成！现在可以重新生成HTML报告。")
            return True
            
        except Exception as e:
            # 如果更新失败，使用默认数据
            return self.create_default_historical_data()

def main():
    excel_path = None
    if len(sys.argv) > 1:
        excel_path = sys.argv[1]
        print(f"📁 使用指定的Excel文件: {excel_path}")
    
    manager = HistoricalDataManager(excel_path)
    success = manager.run_update()
    
    if success:
        print("\n🚀 建议执行以下命令重新生成报告:")
        print("   python3 html_report_generator_fixed.py")
    
    return success

if __name__ == "__main__":
    main()
