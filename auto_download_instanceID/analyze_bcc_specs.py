#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import csv
from typing import Optional


def find_latest_bcc_csv(bcc_dir="bcc_csv"):
    """在指定目录中查找最新的 bcc_instances_*.csv 文件"""
    pattern = os.path.join(bcc_dir, "bcc_instances_*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    # 按修改时间排序，取最新
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def split_by_spec(csv_path):
    """根据实例规格(I列)将实例ID(A列)分类输出到指定目录下的 txt 文件"""
    # 输出文件路径
    h_dir = "/opt/Gpu_H20withL20"
    h800_dir = "/opt/Gpu_h800"
    bcc_dir = "/opt/BCC_Bcm"

    os.makedirs(h_dir, exist_ok=True)
    os.makedirs(h800_dir, exist_ok=True)
    os.makedirs(bcc_dir, exist_ok=True)

    h20_path = os.path.join(h_dir, "H20.txt")
    l20_path = os.path.join(h_dir, "L20.txt")
    h800_path = os.path.join(h800_dir, "H800.txt")
    bcc_path = os.path.join(bcc_dir, "BCC.txt")

    # 先清空已有文件
    for p in (h20_path, l20_path, h800_path, bcc_path):
        if os.path.exists(p):
            os.remove(p)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bcc_id = (row.get("BCC_ID") or "").strip()
            spec = (row.get("实例规格") or "").strip().lower()
            if not bcc_id:
                continue

            # 分类规则：先匹配 h800，再匹配 h20/l20
            if "h800" in spec:
                target = h800_path
            elif "h20" in spec:
                target = h20_path
            elif "l20" in spec:
                target = l20_path
            else:
                target = bcc_path

            with open(target, "a", encoding="utf-8") as out:
                out.write(bcc_id + "\n")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bcc_dir = os.path.join(base_dir, "bcc_csv")

    latest_csv = find_latest_bcc_csv(bcc_dir)
    if not latest_csv:
        print("未在 bcc_csv 目录中找到任何 bcc_instances_*.csv 文件，请先在周一跑一次 run.py 下载 BCC 列表。")
        return

    print(f"使用最新的 BCC CSV: {os.path.relpath(latest_csv, base_dir)}")
    split_by_spec(latest_csv)
    print("分类完成，已生成: /opt/Gpu_H20withL20/H20.txt, /opt/Gpu_H20withL20/L20.txt, /opt/Gpu_h800/H800.txt, /opt/BCC_Bcm/BCC.txt")


if __name__ == "__main__":
    main()

