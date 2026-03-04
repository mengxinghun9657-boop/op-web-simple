#!/usr/bin/env python3
"""
集群管理平台 - 交互式诊断工具
整合所有测试脚本，提供统一的诊断入口
"""
import os
import sys
import subprocess
from typing import Optional

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    """打印信息"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def run_script(script_name: str, description: str) -> bool:
    """
    运行指定的测试脚本
    
    Args:
        script_name: 脚本文件名
        description: 脚本描述
        
    Returns:
        是否成功执行
    """
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    if not os.path.exists(script_path):
        print_error(f"脚本不存在: {script_path}")
        return False
    
    print_info(f"执行: {description}")
    print(f"{Colors.OKBLUE}脚本: {script_name}{Colors.ENDC}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=os.path.dirname(os.path.dirname(script_path)),
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print_success(f"{description} - 执行成功")
            return True
        else:
            print_error(f"{description} - 执行失败 (退出码: {result.returncode})")
            return False
            
    except Exception as e:
        print_error(f"{description} - 执行异常: {str(e)}")
        return False

def show_menu():
    """显示主菜单"""
    print_header("集群管理平台 - 诊断工具")
    
    print(f"{Colors.BOLD}可用的诊断选项：{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}1.{Colors.ENDC} 检查告警记录的severity字段")
    print(f"   {Colors.OKCYAN}→ 查看数据库中severity字段的实际值{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}→ 脚本: check_severity.py{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}2.{Colors.ENDC} 检查告警记录的时间戳问题")
    print(f"   {Colors.OKCYAN}→ 验证时区转换问题和修复效果{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}→ 脚本: check_timestamp.py{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}3.{Colors.ENDC} 测试诊断报告解析逻辑")
    print(f"   {Colors.OKCYAN}→ 验证composedResult字段解析是否正确{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}→ 脚本: test_diagnosis_parse.py{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}4.{Colors.ENDC} 验证修复效果（综合测试）")
    print(f"   {Colors.OKCYAN}→ 运行所有诊断脚本，验证修复效果{Colors.ENDC}")
    print(f"   {Colors.OKCYAN}→ 脚本: verify_fix.py{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}5.{Colors.ENDC} 运行所有诊断脚本")
    print(f"   {Colors.OKCYAN}→ 依次执行所有诊断脚本{Colors.ENDC}\n")
    
    print(f"{Colors.OKGREEN}0.{Colors.ENDC} 退出\n")

def run_all_diagnostics():
    """运行所有诊断脚本"""
    print_header("运行所有诊断脚本")
    
    scripts = [
        ("check_severity.py", "检查severity字段"),
        ("check_timestamp.py", "检查时间戳问题"),
        ("test_diagnosis_parse.py", "测试诊断解析"),
        ("verify_fix.py", "验证修复效果"),
    ]
    
    results = []
    for script_name, description in scripts:
        success = run_script(script_name, description)
        results.append((description, success))
        print()  # 空行分隔
    
    # 打印总结
    print_header("诊断结果总结")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for description, success in results:
        if success:
            print_success(f"{description}")
        else:
            print_error(f"{description}")
    
    print(f"\n{Colors.BOLD}总计: {success_count}/{total_count} 通过{Colors.ENDC}")
    
    if success_count == total_count:
        print_success("所有诊断脚本执行成功！")
    else:
        print_warning(f"有 {total_count - success_count} 个诊断脚本执行失败")

def main():
    """主函数"""
    while True:
        show_menu()
        
        try:
            choice = input(f"{Colors.BOLD}请选择 (0-5): {Colors.ENDC}").strip()
            
            if choice == "0":
                print_info("退出诊断工具")
                break
            elif choice == "1":
                run_script("check_severity.py", "检查severity字段")
            elif choice == "2":
                run_script("check_timestamp.py", "检查时间戳问题")
            elif choice == "3":
                run_script("test_diagnosis_parse.py", "测试诊断解析")
            elif choice == "4":
                run_script("verify_fix.py", "验证修复效果")
            elif choice == "5":
                run_all_diagnostics()
            else:
                print_warning("无效的选择，请输入 0-5")
            
            # 等待用户按键继续
            if choice != "0":
                input(f"\n{Colors.BOLD}按回车键继续...{Colors.ENDC}")
                # 清屏（可选）
                os.system('clear' if os.name == 'posix' else 'cls')
                
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}用户中断{Colors.ENDC}")
            break
        except Exception as e:
            print_error(f"发生错误: {str(e)}")
            input(f"\n{Colors.BOLD}按回车键继续...{Colors.ENDC}")

if __name__ == "__main__":
    main()
