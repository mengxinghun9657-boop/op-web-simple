#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化规则模板数据

实现需求：
- Requirements 8.1: 提供至少 10 个常见场景的规则模板
- Requirements 8.2: 包含 IP 查询、实例 ID 查询、统计查询、报告查询、知识查询等模板类型
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.deps import SessionLocal
from app.models.rule_template import RuleTemplate
from sqlalchemy.exc import IntegrityError


def init_templates():
    """初始化规则模板数据"""
    
    templates = [
        {
            "name": "IP地址查询",
            "category": "强制规则",
            "description": "匹配包含IP地址的查询",
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "intent_type": "sql",
            "priority": 95,
            "metadata": {
                "recommended_tables": ["iaas_servers", "mydb.bce_bcc_instances"],
                "keywords": ["IP", "地址"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "实例ID查询",
            "category": "强制规则",
            "description": "匹配包含实例ID的查询（i-xxx格式）",
            "pattern": r"\bi-[a-zA-Z0-9]+\b",
            "intent_type": "sql",
            "priority": 95,
            "metadata": {
                "recommended_tables": ["iaas_instances", "mydb.bce_bcc_instances"],
                "keywords": ["实例", "instance"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "主机名查询",
            "category": "强制规则",
            "description": "匹配包含主机名的查询",
            "pattern": r"主机名|hostname",
            "intent_type": "sql",
            "priority": 90,
            "metadata": {
                "recommended_tables": ["iaas_servers"],
                "keywords": ["主机名", "hostname"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "统计查询",
            "category": "业务规则",
            "description": "匹配统计类查询（数量、总数、平均等）",
            "pattern": r"(多少|数量|总数|平均|统计|count|sum|avg)",
            "intent_type": "sql",
            "priority": 70,
            "metadata": {
                "recommended_tables": ["iaas_servers", "iaas_instances"],
                "keywords": ["统计", "数量", "总数"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "状态查询",
            "category": "业务规则",
            "description": "匹配状态查询（运行中、停止、异常等）",
            "pattern": r"(状态|运行|停止|异常|正常|active|stopped)",
            "intent_type": "sql",
            "priority": 75,
            "metadata": {
                "recommended_tables": ["iaas_instances", "mydb.bce_bcc_instances"],
                "keywords": ["状态", "运行", "停止"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "配置查询",
            "category": "业务规则",
            "description": "匹配配置信息查询（CPU、内存、磁盘等）",
            "pattern": r"(配置|CPU|内存|磁盘|memory|disk|vcpu)",
            "intent_type": "sql",
            "priority": 70,
            "metadata": {
                "recommended_tables": ["iaas_servers", "iaas_instances"],
                "keywords": ["配置", "CPU", "内存"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "知识库查询",
            "category": "通用规则",
            "description": "匹配知识库相关查询（如何、怎么、方法等）",
            "pattern": r"(如何|怎么|怎样|方法|步骤|教程|指南)",
            "intent_type": "rag_knowledge",
            "priority": 60,
            "metadata": {
                "keywords": ["如何", "方法", "步骤"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "报告查询",
            "category": "通用规则",
            "description": "匹配报告相关查询（分析、报告、总结等）",
            "pattern": r"(分析|报告|总结|趋势|预测)",
            "intent_type": "rag_report",
            "priority": 55,
            "metadata": {
                "keywords": ["分析", "报告", "总结"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "故障排查",
            "category": "业务规则",
            "description": "匹配故障排查相关查询",
            "pattern": r"(故障|问题|错误|异常|报错|失败)",
            "intent_type": "rag_knowledge",
            "priority": 80,
            "metadata": {
                "keywords": ["故障", "问题", "错误"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "监控数据查询",
            "category": "业务规则",
            "description": "匹配监控数据查询（CPU使用率、内存使用率等）",
            "pattern": r"(监控|使用率|负载|性能|metrics)",
            "intent_type": "sql",
            "priority": 75,
            "metadata": {
                "recommended_tables": ["mydb.bce_bcc_instances", "mydb.bce_cce_nodes"],
                "keywords": ["监控", "使用率", "性能"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "集群查询",
            "category": "业务规则",
            "description": "匹配集群相关查询",
            "pattern": r"(集群|cluster|cce|kubernetes|k8s)",
            "intent_type": "sql",
            "priority": 80,
            "metadata": {
                "recommended_tables": ["mydb.bce_cce_clusters", "mydb.bce_cce_nodes"],
                "keywords": ["集群", "cluster", "cce"]
            },
            "is_system": True,
            "created_by": "system"
        },
        {
            "name": "时间范围查询",
            "category": "业务规则",
            "description": "匹配时间范围查询（今天、昨天、最近等）",
            "pattern": r"(今天|昨天|本周|本月|最近|过去|近期)",
            "intent_type": "sql",
            "priority": 65,
            "metadata": {
                "keywords": ["今天", "昨天", "最近"]
            },
            "is_system": True,
            "created_by": "system"
        }
    ]
    
    db = SessionLocal()
    try:
        added_count = 0
        skipped_count = 0
        
        for template_data in templates:
            # 检查是否已存在
            existing = db.query(RuleTemplate).filter(
                RuleTemplate.name == template_data["name"]
            ).first()
            
            if existing:
                print(f"⏭️  跳过已存在的模板: {template_data['name']}")
                skipped_count += 1
                continue
            
            # 创建新模板
            # 将 metadata 键重命名为 rule_metadata（匹配模型字段名）
            if "metadata" in template_data:
                template_data["rule_metadata"] = template_data.pop("metadata")
            
            template = RuleTemplate(**template_data)
            db.add(template)
            added_count += 1
            print(f"✅ 添加模板: {template_data['name']}")
        
        db.commit()
        
        print(f"\n📊 初始化完成:")
        print(f"   - 新增模板: {added_count} 个")
        print(f"   - 跳过模板: {skipped_count} 个")
        print(f"   - 总计模板: {added_count + skipped_count} 个")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 开始初始化规则模板数据...")
    success = init_templates()
    sys.exit(0 if success else 1)
