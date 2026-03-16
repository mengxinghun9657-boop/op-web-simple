#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI 服务模块（保留基础AI功能）
"""

from .ernie_client import ERNIEClient, get_ernie_client, close_ernie_client

__all__ = [
    "ERNIEClient",
    "get_ernie_client",
    "close_ernie_client",
]
