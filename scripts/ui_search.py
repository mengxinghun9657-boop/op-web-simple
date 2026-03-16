#!/usr/bin/env python3
"""
UI/UX Pro Max 搜索工具
使用方法：python3 scripts/ui_search.py <query> [options]
"""
import sys
import os

# 添加UI/UX Pro Max到路径
ui_ux_path = os.path.join(os.path.dirname(__file__), '../.shared/ui-ux-pro-max/scripts')
sys.path.insert(0, ui_ux_path)

from core import search, search_stack, AVAILABLE_STACKS
import json


def print_help():
    print("""
UI/UX Pro Max 设计指南搜索工具

用法：
    python3 scripts/ui_search.py <query> [options]

选项：
    --domain <domain>       指定搜索领域
    --stack <stack>         搜索技术栈特定指南
    --max-results <n>       最大结果数（默认：3）
    --json                  JSON格式输出

可用领域：
    style       UI设计风格（Glassmorphism, Neumorphism等）
    color       配色方案
    typography  字体配对建议
    chart       图表类型选择
    landing     落地页模式
    product     产品类型设计（29种）
    ux          UX最佳实践和可访问性
    prompt      AI提示词和CSS实现

可用技术栈：
    react, nextjs, vue, nuxtjs, nuxt-ui, svelte
    swiftui, react-native, flutter, html-tailwind

示例：
    python3 scripts/ui_search.py "dark mode dashboard"
    python3 scripts/ui_search.py "fintech palette" --domain color
    python3 scripts/ui_search.py "button hover" --stack react
    python3 scripts/ui_search.py "landing page" --domain landing --max-results 5
    python3 scripts/ui_search.py "glassmorphism" --json
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print_help()
        sys.exit(0)

    # 解析参数
    query = sys.argv[1]
    domain = None
    stack = None
    max_results = 3
    json_output = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--domain' and i + 1 < len(sys.argv):
            domain = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--stack' and i + 1 < len(sys.argv):
            stack = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--max-results' and i + 1 < len(sys.argv):
            max_results = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--json':
            json_output = True
            i += 1
        else:
            i += 1

    # 执行搜索
    try:
        if stack:
            result = search_stack(query, stack, max_results=max_results)
        else:
            result = search(query, domain=domain, max_results=max_results)

        if json_output:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # 格式化输出
            print(f"\n{'='*70}")
            print(f"🎨 UI/UX Pro Max 搜索结果")
            print(f"{'='*70}\n")

            if stack:
                print(f"📚 技术栈: {stack}")
            elif domain:
                print(f"📂 领域: {domain}")

            print(f"🔍 查询: {query}")
            print(f"📊 结果数: {result.get('count', 0)}\n")

            if result.get('results'):
                for idx, item in enumerate(result['results'], 1):
                    print(f"{'─'*70}")
                    print(f"结果 #{idx}")
                    print(f"{'─'*70}")

                    for key, value in item.items():
                        if value and value != 'N/A':
                            # 美化键名
                            key_display = key.replace('_', ' ').title()
                            print(f"  {key_display}: {value}")
                    print()
            else:
                print("❌ 未找到相关结果\n")

    except Exception as e:
        print(f"❌ 搜索出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
