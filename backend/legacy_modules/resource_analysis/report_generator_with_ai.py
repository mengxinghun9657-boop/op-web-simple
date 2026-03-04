#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
资源分析报告生成器（带AI解读）
在原有报告基础上添加AI智能解读模块
"""

import asyncio
from typing import Dict, Any
from loguru import logger


async def generate_ai_interpretation_html(analysis_result: Dict[str, Any]) -> str:
    """
    生成AI解读HTML
    
    Args:
        analysis_result: 分析结果
        
    Returns:
        AI解读HTML内容
    """
    try:
        from app.services.ai.resource_report_ai_interpreter import get_resource_report_ai_interpreter
        
        ai_interpreter = get_resource_report_ai_interpreter()
        
        # 生成AI解读
        ai_html = await ai_interpreter.generate_interpretation(
            report_type='resource_analysis',
            analysis_data={'analysis_result': analysis_result}
        )
        
        return ai_html
        
    except Exception as e:
        logger.error(f"生成AI解读失败: {e}")
        return '''
        <div class="ai-interpretation-error">
            <p>⚠️ AI解读暂时不可用</p>
        </div>
        <style>
        .ai-interpretation-error {
            padding: 20px;
            background: #fff3e0;
            border-radius: 8px;
            text-align: center;
            color: #ff9800;
        }
        </style>
        '''


def insert_ai_interpretation_tab(html_content: str, ai_html: str) -> str:
    """
    在HTML中插入AI解读标签页
    
    Args:
        html_content: 原始HTML内容
        ai_html: AI解读HTML
        
    Returns:
        插入AI解读后的HTML
    """
    # 1. 在导航标签中添加AI解读标签（放在第一个位置）
    nav_tabs_marker = '<div class="nav-tabs">'
    nav_tabs_insert = '''<div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('ai-insights')">🤖 AI智能解读</button>'''
    
    html_content = html_content.replace(nav_tabs_marker, nav_tabs_insert, 1)
    
    # 2. 将原来的第一个标签页改为非active
    html_content = html_content.replace(
        '<button class="nav-tab active" onclick="showTab(\'overview\')">',
        '<button class="nav-tab" onclick="showTab(\'overview\')">',
        1
    )
    
    # 3. 在第一个tab-content之前插入AI解读内容
    first_tab_marker = '<div id="overview" class="tab-content active">'
    ai_tab_content = f'''
        <!-- AI智能解读标签页 -->
        <div id="ai-insights" class="tab-content active">
            <div class="ai-interpretation-section">
                <div class="ai-header">
                    <h2>🤖 AI智能解读</h2>
                    <p class="ai-subtitle">基于42个关键指标的智能分析与建议</p>
                </div>
                {ai_html}
            </div>
        </div>

        <div id="overview" class="tab-content">'''
    
    html_content = html_content.replace(first_tab_marker, ai_tab_content, 1)
    
    # 4. 添加AI解读相关的CSS样式
    ai_styles = '''
        /* AI解读样式 */
        .ai-interpretation-section {
            padding: 20px;
        }
        .ai-header {
            text-align: center;
            margin-bottom: 40px;
        }
        .ai-header h2 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #1976D2 0%, #42A5F5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }
        .ai-subtitle {
            color: #64748b;
            font-size: 1.1em;
        }
    </style>
</head>'''
    
    html_content = html_content.replace('</style>\n</head>', ai_styles, 1)
    
    return html_content


async def generate_resource_report_with_ai(
    analyzer,
    analysis_result: Dict[str, Any],
    output_path: str
) -> str:
    """
    生成带AI解读的资源分析报告
    
    Args:
        analyzer: ResourceAnalyzer实例
        analysis_result: 分析结果
        output_path: 输出路径
        
    Returns:
        生成的报告路径
    """
    try:
        logger.info("📝 开始生成带AI解读的资源分析报告...")
        
        # 1. 生成原始HTML报告
        logger.info("生成基础HTML报告...")
        analyzer.generate_extended_html_report(analysis_result, output_path)
        
        # 2. 读取生成的HTML
        with open(output_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 3. 生成AI解读
        logger.info("生成AI解读...")
        ai_html = await generate_ai_interpretation_html(analysis_result)
        
        # 4. 插入AI解读到HTML中
        logger.info("插入AI解读到报告中...")
        enhanced_html = insert_ai_interpretation_tab(html_content, ai_html)
        
        # 5. 保存增强后的HTML
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_html)
        
        logger.info(f"✅ 带AI解读的报告已生成: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"❌ 生成带AI解读的报告失败: {e}")
        # 如果失败，至少保证原始报告可用
        return output_path
