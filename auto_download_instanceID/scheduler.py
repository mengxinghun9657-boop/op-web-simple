#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import subprocess
import logging
from datetime import datetime, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bcc_scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_bcc_download():
    """执行BCC数据下载任务"""
    try:
        import os
        import sys
        
        logging.info("开始执行BCC数据下载任务")
        
        # 获取当前脚本目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 使用当前Python解释器
        python_exe = sys.executable
        
        # 兼容Python 3.5+：不使用 text 参数，手动decode
        result = subprocess.run([python_exe, 'run.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              cwd=script_dir)
        
        # 手动将bytes转为str
        stdout_str = result.stdout.decode('utf-8') if result.stdout else ''
        stderr_str = result.stderr.decode('utf-8') if result.stderr else ''
        
        if result.returncode == 0:
            logging.info("BCC数据下载成功")
            if stdout_str:
                logging.info(f"输出: {stdout_str}")
        else:
            logging.error(f"BCC数据下载失败: {stderr_str}")
            
    except Exception as e:
        logging.error(f"执行下载任务时出错: {e}")

def is_monday_9am():
    """检查是否为周一上午9点"""
    now = datetime.now()
    return now.weekday() == 0 and now.hour == 9 and now.minute == 0

def main():
    logging.info("BCC数据定时下载器已启动")
    logging.info("计划任务: 每周一上午9:00执行数据下载")
    
    last_run_date = None
    
    # 启动时立即检查一次是否需要下载
    logging.info("检查是否需要下载本周数据")
    run_bcc_download()
    last_run_date = datetime.now().date()
    
    while True:
        now = datetime.now()
        
        # 检查是否为周一上午9点且今天还未执行过
        if is_monday_9am() and last_run_date != now.date():
            logging.info("触发定时任务")
            run_bcc_download()
            last_run_date = now.date()
        
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    main()
