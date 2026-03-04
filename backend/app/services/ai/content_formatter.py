#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内容格式化工具（Content Formatter）

实现需求：
- Requirements 28.1: JSON 到 Markdown 表格转换
- Requirements 28.2: 数组到 Markdown 列表转换
- Requirements 28.3: 嵌套 JSON 扁平化（点号表示层级）
- Requirements 28.4, 28.5: 内容截断（超过 2000 字符）
- Requirements 28.6: 在 Prompt 中明确说明数据格式为 Markdown 表格

功能：
- 将复杂的 JSON 数据转换为易读的 Markdown 格式
- 支持嵌套结构的扁平化处理
- 自动截断过长内容并添加标记
- 保持数据可读性，减少 AI 幻觉
"""

import json
from typing import Any, Dict, List, Union
from app.core.logger import logger


class ContentFormatter:
    """
    内容格式化工具类
    
    提供多种数据格式转换功能，将复杂的 JSON 数据转换为
    易于 AI 理解的 Markdown 格式。
    
    使用示例：
    ```python
    formatter = ContentFormatter()
    
    # JSON 转 Markdown 表格
    data = {"name": "server1", "cpu": 80, "memory": 90}
    markdown = formatter.json_to_markdown(data)
    
    # 数组转 Markdown 列表
    items = ["item1", "item2", "item3"]
    markdown = formatter.array_to_markdown(items)
    
    # 格式化详情数据（自动选择格式）
    formatted = formatter.format_detail_data(complex_data)
    ```
    """
    
    def __init__(self, max_length: int = 2000, max_nesting_level: int = 2):
        """
        初始化内容格式化器
        
        Args:
            max_length: 最大内容长度（默认2000字符）
            max_nesting_level: 最大嵌套层级（默认2层）
        """
        self.max_length = max_length
        self.max_nesting_level = max_nesting_level
        logger.info(f"ContentFormatter initialized: max_length={max_length}, max_nesting_level={max_nesting_level}")
    
    def json_to_markdown(self, data: Dict[str, Any], title: str = None) -> str:
        """
        将 JSON 对象转换为 Markdown 表格
        
        Args:
            data: JSON 对象（字典）
            title: 表格标题（可选）
        
        Returns:
            str: Markdown 表格格式的字符串
        
        Validates: Requirements 28.1
        
        示例：
        输入: {"name": "server1", "cpu": 80, "memory": 90}
        输出:
        | 字段 | 值 |
        |------|-----|
        | name | server1 |
        | cpu | 80 |
        | memory | 90 |
        """
        if not isinstance(data, dict):
            logger.warning(f"json_to_markdown: data is not a dict, type={type(data)}")
            return str(data)
        
        if not data:
            return "*（无数据）*"
        
        # 扁平化嵌套结构
        flattened = self.flatten_json(data)
        
        # 构建 Markdown 表格
        lines = []
        
        if title:
            lines.append(f"**{title}**\n")
        
        lines.append("| 字段 | 值 |")
        lines.append("|------|-----|")
        
        for key, value in flattened.items():
            # 处理特殊字符（避免破坏表格格式）
            key_str = str(key).replace("|", "\\|").replace("\n", " ")
            value_str = self._format_value(value).replace("|", "\\|").replace("\n", " ")
            
            lines.append(f"| {key_str} | {value_str} |")
        
        markdown = "\n".join(lines)
        
        logger.debug(f"json_to_markdown: converted {len(data)} fields to markdown table")
        
        return markdown
    
    def array_to_markdown(self, items: List[Any], title: str = None, ordered: bool = False) -> str:
        """
        将数组转换为 Markdown 列表
        
        Args:
            items: 数组
            title: 列表标题（可选）
            ordered: 是否使用有序列表（默认无序）
        
        Returns:
            str: Markdown 列表格式的字符串
        
        Validates: Requirements 28.2
        
        示例：
        输入: ["item1", "item2", "item3"]
        输出:
        - item1
        - item2
        - item3
        """
        if not isinstance(items, list):
            logger.warning(f"array_to_markdown: items is not a list, type={type(items)}")
            return str(items)
        
        if not items:
            return "*（无数据）*"
        
        lines = []
        
        if title:
            lines.append(f"**{title}**\n")
        
        for i, item in enumerate(items, 1):
            # 如果是字典，转换为表格
            if isinstance(item, dict):
                item_markdown = self.json_to_markdown(item)
                prefix = f"{i}. " if ordered else "- "
                lines.append(f"{prefix}条目 {i}:")
                lines.append(item_markdown)
                lines.append("")  # 空行分隔
            else:
                # 简单值，直接列出
                value_str = self._format_value(item)
                prefix = f"{i}. " if ordered else "- "
                lines.append(f"{prefix}{value_str}")
        
        markdown = "\n".join(lines)
        
        logger.debug(f"array_to_markdown: converted {len(items)} items to markdown list")
        
        return markdown
    
    def flatten_json(self, data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
        """
        扁平化嵌套 JSON（使用点号表示层级）
        
        Args:
            data: 嵌套的 JSON 对象
            parent_key: 父键名（递归使用）
            sep: 分隔符（默认为点号）
        
        Returns:
            Dict: 扁平化后的字典
        
        Validates: Requirements 28.3
        
        示例：
        输入: {"cluster": {"metrics": {"cpu": 80}}}
        输出: {"cluster.metrics.cpu": 80}
        """
        items = []
        
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            
            # 检查嵌套层级
            current_level = new_key.count(sep)
            
            if isinstance(value, dict) and current_level < self.max_nesting_level:
                # 递归扁平化嵌套字典
                items.extend(self.flatten_json(value, new_key, sep=sep).items())
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                # 处理字典数组：为每个元素创建索引
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        indexed_key = f"{new_key}[{i}]"
                        items.extend(self.flatten_json(item, indexed_key, sep=sep).items())
                    else:
                        items.append((f"{new_key}[{i}]", item))
            else:
                # 叶子节点
                items.append((new_key, value))
        
        flattened = dict(items)
        
        logger.debug(f"flatten_json: flattened {len(data)} keys to {len(flattened)} keys")
        
        return flattened
    
    def truncate_content(self, content: str, max_length: int = None) -> str:
        """
        截断过长内容
        
        Args:
            content: 原始内容
            max_length: 最大长度（默认使用实例配置）
        
        Returns:
            str: 截断后的内容（如果超长会添加标记）
        
        Validates: Requirements 28.4, 28.5
        """
        if max_length is None:
            max_length = self.max_length
        
        if len(content) <= max_length:
            return content
        
        # 截断并添加标记
        truncated = content[:max_length]
        truncated += "\n\n**[数据已精简]**"
        
        logger.info(f"truncate_content: truncated from {len(content)} to {len(truncated)} chars")
        
        return truncated
    
    def format_detail_data(
        self,
        data: Any,
        title: str = None,
        include_prompt_hint: bool = True
    ) -> str:
        """
        格式化详情数据（自动选择最佳格式）
        
        根据数据类型自动选择合适的格式化方式：
        - 字典 → Markdown 表格
        - 数组 → Markdown 列表
        - 其他 → 字符串
        
        Args:
            data: 要格式化的数据
            title: 标题（可选）
            include_prompt_hint: 是否包含 Prompt 提示（默认 True）
        
        Returns:
            str: 格式化后的 Markdown 内容
        
        Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5, 28.6
        """
        try:
            # 如果是字符串，尝试解析为 JSON
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    # 不是 JSON，直接返回
                    return self.truncate_content(data)
            
            # 根据类型选择格式化方式
            if isinstance(data, dict):
                markdown = self.json_to_markdown(data, title=title)
            elif isinstance(data, list):
                markdown = self.array_to_markdown(data, title=title)
            else:
                markdown = str(data)
            
            # 截断过长内容
            markdown = self.truncate_content(markdown)
            
            # 添加 Prompt 提示（Requirements 28.6）
            if include_prompt_hint:
                hint = "\n\n*注：以上数据已格式化为 Markdown 表格/列表，请直接理解表格内容。*"
                markdown += hint
            
            logger.debug(f"format_detail_data: formatted data, final length={len(markdown)}")
            
            return markdown
        
        except Exception as e:
            logger.error(f"format_detail_data failed: {e}")
            # 降级：返回原始字符串
            return self.truncate_content(str(data))
    
    def format_metadata_for_ai(
        self,
        metadata: Dict[str, Any],
        summary: str = None,
        conclusion: str = None
    ) -> str:
        """
        格式化知识条目的 metadata 字段供 AI 使用
        
        将详情层数据格式化为易读的 Markdown 格式，
        配合摘要层和结论层一起传递给 AI。
        
        Args:
            metadata: 详情层数据（JSON 格式）
            summary: 摘要层内容（可选）
            conclusion: 结论层内容（可选）
        
        Returns:
            str: 完整的格式化内容
        
        Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5, 28.6
        """
        sections = []
        
        # 摘要层
        if summary:
            sections.append("## 摘要")
            sections.append(summary)
            sections.append("")
        
        # 结论层
        if conclusion:
            sections.append("## 关键结论")
            sections.append(conclusion)
            sections.append("")
        
        # 详情层
        if metadata:
            sections.append("## 详细数据")
            
            # 格式化 metadata
            detail_markdown = self.format_detail_data(
                metadata,
                title=None,
                include_prompt_hint=True
            )
            
            sections.append(detail_markdown)
        
        full_content = "\n".join(sections)
        
        # 最终截断检查
        if len(full_content) > self.max_length:
            logger.warning(f"format_metadata_for_ai: content too long ({len(full_content)} chars), truncating...")
            full_content = self.truncate_content(full_content)
        
        return full_content
    
    def _format_value(self, value: Any) -> str:
        """
        格式化单个值
        
        Args:
            value: 要格式化的值
        
        Returns:
            str: 格式化后的字符串
        """
        if value is None:
            return "*（空）*"
        elif isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # 简单数组，用逗号分隔
            if len(value) <= 5:
                return ", ".join(str(v) for v in value)
            else:
                # 太长，只显示前几个
                preview = ", ".join(str(v) for v in value[:5])
                return f"{preview}, ... (共{len(value)}项)"
        elif isinstance(value, dict):
            # 嵌套字典，转为 JSON 字符串
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)


# 全局实例（可选）
_content_formatter = None


def get_content_formatter(
    max_length: int = 2000,
    max_nesting_level: int = 2
) -> ContentFormatter:
    """获取内容格式化器实例"""
    global _content_formatter
    
    if _content_formatter is None:
        _content_formatter = ContentFormatter(
            max_length=max_length,
            max_nesting_level=max_nesting_level
        )
    
    return _content_formatter
