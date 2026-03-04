#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
icafe 运营数据分析模块

提供以下功能：
- Excel 文件数据分析
- icafe API 数据查询
- HTML 报告生成
"""

from .config import IcafeConfig
from .analyzer import OperationalAnalyzer
from .report_generator import ReportGenerator
from .api_client import IcafeAPIClient

__all__ = [
    'IcafeConfig',
    'OperationalAnalyzer', 
    'ReportGenerator',
    'IcafeAPIClient'
]
