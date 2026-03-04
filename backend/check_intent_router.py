#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 intent_router.py 是否包含 IP 地址检测代码
"""

import os

def check_intent_router():
    """检查 intent_router.py 文件内容"""
    
    file_path = "/app/app/services/ai/intent_router.py"
    
    print("=" * 60)
    print("检查 intent_router.py 文件")
    print("=" * 60)
    print(f"文件路径: {file_path}\n")
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键代码片段
    checks = [
        ("IP 地址检测注释", "# 0. 强制规则：检测 IP 地址"),
        ("IP 正则表达式", "ip_pattern = r'\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b'"),
        ("IP 检测逻辑", "if re.search(ip_pattern, query):"),
        ("强制路由日志", "检测到 IP 地址，强制路由到 SQL 查询"),
        ("返回 SQL 意图", "return self.INTENT_SQL, 0.95, [self.INTENT_SQL]"),
    ]
    
    print("检查关键代码片段:")
    print("-" * 60)
    
    all_found = True
    
    for name, code_snippet in checks:
        if code_snippet in content:
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - 未找到")
            all_found = False
    
    print("\n" + "=" * 60)
    
    if all_found:
        print("✅ 所有关键代码片段都存在！")
        print("\n建议：重启后端服务以确保代码生效")
        print("docker-compose -f docker-compose.prod.yml restart backend")
    else:
        print("❌ 部分代码片段缺失！")
        print("\n需要更新容器内的代码：")
        print("1. 在本地修改 backend/app/services/ai/intent_router.py")
        print("2. 使用 pack-offline.sh 重新打包")
        print("3. 部署到服务器")
    
    print("=" * 60)
    
    return all_found


if __name__ == "__main__":
    check_intent_router()
