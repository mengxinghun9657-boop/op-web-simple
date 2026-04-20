#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
报告 AI 解读服务
在生成 HTML 报告时，调用 ERNIE AI 生成智能解读部分
"""

import json
from typing import Dict, Any, Optional
from loguru import logger

from app.services.ai.ernie_client import ERNIEClient, get_ernie_client_with_db_config
from app.services.ai.trend_analysis_engine import TrendAnalysisEngine
from app.core.config import settings


class ReportAIInterpreter:
    """报告 AI 解读服务"""

    def __init__(self, ernie_client: Optional[ERNIEClient] = None, db=None):
        """
        初始化报告 AI 解读服务

        Args:
            ernie_client: ERNIE 客户端实例（优先使用）
            db: SQLAlchemy Session，用于读取数据库中的 AI 配置
        """
        if ernie_client is not None:
            self.ernie_client = ernie_client
        else:
            self.ernie_client = get_ernie_client_with_db_config(db=db)
        self.trend_engine = TrendAnalysisEngine()
        logger.info("✅ 报告 AI 解读服务初始化成功")
    
    async def generate_interpretation(
        self,
        report_type: str,
        analysis_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        生成报告的 AI 解读
        
        Args:
            report_type: 报告类型（resource_analysis, bcc_monitoring, bos_monitoring, operational_analysis）
            analysis_data: 分析数据
        
        Returns:
            Optional[str]: AI 解读内容（HTML 格式），失败返回 None
        """
        try:
            logger.info(f"📝 开始生成 {report_type} 的 AI 解读...")
            
            # 1. 准备提示词
            prompt = self._prepare_prompt(report_type, analysis_data)
            
            # 2. 调用 AI 生成解读
            interpretation_text = await self.ernie_client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            if not interpretation_text:
                logger.warning(f"⚠️ AI 返回空响应: {report_type}")
                return None
            
            # 3. 转换为 HTML 格式
            html_content = self._format_as_html(interpretation_text)
            
            logger.info(f"✅ AI 解读生成成功: {report_type}")
            return html_content
            
        except Exception as e:
            logger.error(f"❌ 生成 AI 解读失败: {report_type}, 错误: {e}")
            return None
    
    def _prepare_prompt(self, report_type: str, analysis_data: Dict[str, Any]) -> str:
        """
        准备 AI 提示词
        
        Args:
            report_type: 报告类型
            analysis_data: 分析数据
        
        Returns:
            str: 提示词
        """
        # 提取关键数据
        overview = analysis_data.get('overview', {})
        efficiency_data = analysis_data.get('person_workload', analysis_data.get('efficiency_data', []))
        hardware_summary = analysis_data.get('hardware_summary', {})
        weekly_trends = analysis_data.get('weekly_trends', [])
        
        # 根据报告类型生成不同的提示词
        if report_type == 'operational_analysis':
            quality_metrics = analysis_data.get('quality_metrics', {})
            prompt = self._prepare_operational_prompt(overview, efficiency_data, weekly_trends, quality_metrics)
        elif report_type == 'resource_analysis':
            prompt = self._prepare_resource_prompt(overview, analysis_data)
        elif report_type in ['bcc_monitoring', 'bos_monitoring']:
            prompt = self._prepare_monitoring_prompt(report_type, overview, analysis_data)
        else:
            prompt = self._prepare_generic_prompt(report_type, analysis_data)
        
        return prompt
    
    def _prepare_operational_prompt(
        self,
        overview: Dict,
        efficiency_data: list,
        weekly_trends: list,
        quality_metrics: Dict = None
    ) -> str:
        """准备运营分析的提示词"""
        if quality_metrics is None:
            quality_metrics = {}

        # ── 一、总体指标 ──
        total_cards = overview.get('总卡片数', 0)
        avg_weekly = overview.get('平均每周卡片处理量', 0)
        problem_closure_rate = overview.get('问题闭环率', 'N/A')
        requirement_closure_rate = overview.get('需求闭环率', 'N/A')
        feels_yes = overview.get('有感事件数', 'N/A')
        feels_rate = overview.get('有感率', 'N/A')
        escalated = overview.get('升级到研或OP数', 'N/A')
        escalate_rate = overview.get('升级率', 'N/A')

        # ── 判断时间跨度（决定趋势粒度描述）──
        # weekly_trends 的第一个条目的周期标签：若含 "/" 说明是日粒度，否则为周/月粒度
        period_is_daily = False
        if weekly_trends:
            first_label = weekly_trends[0].get('周期标签') or weekly_trends[0].get('周期', '')
            period_is_daily = '/' in str(first_label) and '-' not in str(first_label).split('/')[0]
        period_desc = "日度" if period_is_daily else "周度"
        trend_section_title = f"近期{period_desc}趋势（最近 {'14 天' if period_is_daily else '12 周'}）"
        forecast_hint = (
            "（注：统计周期较短，趋势预测仅供参考，重点关注日间波动规律）"
            if period_is_daily else ""
        )

        # ── 二、负责人数据（完整列表）──
        workload_lines = ""
        if efficiency_data:
            lines = []
            for p in efficiency_data:
                name = p.get('创建人', '?')
                total = p.get('总卡片数', 0)
                done = p.get('已完成数量', 0)
                undone = p.get('未完成数量', 0)
                lines.append(f"| {name} | {total} | {done} | {undone} |")
            workload_lines = (
                "| 负责人 | 总卡片数 | 已完成 | 未完成 |\n"
                "|--------|---------|--------|--------|\n"
                + "\n".join(lines)
            )

        # ── 三、趋势数据（最多取最近 14 条）──
        weekly_lines = ""
        if weekly_trends:
            recent = weekly_trends[-14:] if len(weekly_trends) > 14 else weekly_trends
            rows = []
            for w in recent:
                label = w.get('周期标签') or w.get('周期', '')
                follow = w.get('问题跟进数', 0)
                close = w.get('闭环个数', 0)
                rate = w.get('问题解决率', 'N/A')
                feels_w = w.get('有感事件数', '-')
                rows.append(f"| {label} | {follow} | {close} | {rate} | {feels_w} |")
            weekly_lines = (
                f"| {period_desc}周期 | 问题跟进数 | 闭环个数 | 解决率 | 有感事件数 |\n"
                "|------|-----------|---------|--------|----------|\n"
                + "\n".join(rows)
            )

        # ── 四、趋势预测（数据点 >= 3 才预测）──
        forecast_lines = ""
        try:
            follow_counts = [w.get('问题跟进数', 0) for w in weekly_trends]
            close_counts = [w.get('闭环个数', 0) for w in weekly_trends]
            if len(follow_counts) >= 3:
                follow_forecast, follow_stats = self.trend_engine.linear_regression_forecast(
                    follow_counts, forecast_periods=1
                )
                close_forecast, close_stats = self.trend_engine.linear_regression_forecast(
                    close_counts, forecast_periods=1
                )
                if follow_forecast and close_forecast:
                    pred_follow = follow_forecast[0]
                    pred_close = close_forecast[0]
                    pred_rate = (pred_close / pred_follow * 100) if pred_follow > 0 else 0
                    trend_dir = (
                        "上升↑" if follow_stats.get('trend') == 'increasing'
                        else "下降↓" if follow_stats.get('trend') == 'decreasing'
                        else "平稳→"
                    )
                    r2 = follow_stats.get('r_squared', 0)
                    next_period = "明日" if period_is_daily else "下周"
                    forecast_lines = (
                        f"- 预测{next_period}问题跟进数：**{pred_follow:.0f} 项**（趋势：{trend_dir}，R²={r2:.2f}）\n"
                        f"- 预测{next_period}闭环数：**{pred_close:.0f} 项**\n"
                        f"- 预测解决率：**{pred_rate:.1f}%**\n"
                        f"> R²={r2:.2f}，{'预测可信度较高' if r2 >= 0.7 else '数据波动较大，预测仅供参考'}"
                    )
        except Exception as e:
            logger.warning(f"趋势预测失败: {e}")

        # ── 五、各产品质量指标（取有感率最高的 Top 5）──
        product_quality_lines = ""
        product_quality = quality_metrics.get('product_quality', [])
        if product_quality:
            def parse_rate(r):
                try:
                    return float(str(r).rstrip('%'))
                except Exception:
                    return 0.0
            top5 = sorted(product_quality, key=lambda x: parse_rate(x.get('有感率', '0%')), reverse=True)[:5]
            rows = []
            for pq in top5:
                rows.append(
                    f"| {pq.get('产品','')} | {pq.get('卡片总数',0)} "
                    f"| {pq.get('有感事件数',0)} | {pq.get('有感率','N/A')} "
                    f"| {pq.get('升级到研或OP数',0)} | {pq.get('升级率','N/A')} |"
                )
            product_quality_lines = (
                "| 产品 | 卡片总数 | 有感事件 | 有感率 | 升级数 | 升级率 |\n"
                "|------|---------|---------|--------|--------|-------|\n"
                + "\n".join(rows)
            )

        # ── 有感/升级数据说明 ──
        has_feels = str(feels_yes) != 'N/A' and str(feels_rate) != 'N/A'
        has_escalate = str(escalated) != 'N/A' and str(escalate_rate) != 'N/A'
        quality_data_note = ""
        if not has_feels and not has_escalate:
            quality_data_note = "（注：当前数据集中无有感事件/升级字段，质量指标部分无数据可分析）"
        elif not has_feels:
            quality_data_note = "（注：当前数据集中无有感事件字段）"
        elif not has_escalate:
            quality_data_note = "（注：当前数据集中无升级字段）"

        feels_row = f"| 有感事件数 | {feels_yes}（有感率 {feels_rate}） |" if has_feels else "| 有感事件数 | 无此字段 |"
        escalate_row = f"| 升级到研或OP数 | {escalated}（升级率 {escalate_rate}） |" if has_escalate else "| 升级到研或OP数 | 无此字段 |"

        # 动态输出要求：短周期时调整"四、趋势分析"的表述
        trend_analysis_req = (
            f"### 四、趋势分析（近 {'14 天' if period_is_daily else '12 周'}）\n"
            f"- 问题跟进数和闭环数的变化方向（上升/下降/震荡），引用具体{'日' if period_is_daily else '周'}数据\n"
            f"- 解决率的波动范围（最高{'日' if period_is_daily else '周'} vs 最低{'日' if period_is_daily else '周'}）\n"
            f"- 有感事件数的{'日' if period_is_daily else '周'}度分布是否有集中爆发"
        )
        forecast_req = (
            "### 五、预测与建议\n"
            + ("- 统计周期较短（日粒度），暂不做下期预测；重点说明当前数据揭示的问题和建议\n"
               if period_is_daily else
               "- 直接引用预测数字（预计下周跟进 N 项、闭环 M 项）\n"
               "- 若 R² < 0.5，说明预测参考价值有限，需关注近 3 周实际数据\n"
               )
            + "- 给出 1 条具体的资源配置建议"
        )

        prompt = f"""你是一位资深运维团队效能分析师，请根据以下结构化数据，生成一份**专业、量化、可操作**的运营分析报告解读。

---

## 数据背景

数据来源：iCafe 项目管理系统
- "未完成"状态包含：进行中、待处理、验证中、长期跟踪等，**不等于工作滞后**
- 同一张卡片可能由多名负责人共同承接，各自独立计入
{quality_data_note}

---

## 输入数据

### 1. 总体指标
| 指标 | 数值 |
|------|------|
| 统计周期总卡片数 | {total_cards} |
| 平均每{period_desc[1]}处理量 | {avg_weekly} |
| 问题闭环率 | {problem_closure_rate} |
| 需求闭环率 | {requirement_closure_rate} |
{feels_row}
{escalate_row}

### 2. 各负责人卡片承接情况

{workload_lines if workload_lines else '（无数据）'}

### 3. {trend_section_title}

{weekly_lines if weekly_lines else '（无数据）'}

### 4. 趋势预测（线性回归）{forecast_hint}

{forecast_lines if forecast_lines else '（数据不足，无法预测）'}

### 5. 各产品质量指标（有感率 Top 5）

{product_quality_lines if product_quality_lines else '（无数据）'}

---

## 输出要求

请严格按照以下 Markdown 结构输出，**每节必须包含具体数字**，禁止空泛描述：

### 一、整体工作量评估
- 说明统计周期总量、问题/需求闭环率的绝对值，并与行业参考水平（问题闭环率 >70% 为良好）作对比
- 如果闭环率偏低，指出未完成卡片中占比最多的状态

### 二、卡片分布均衡性
- 计算负责人承接卡片数的**最大值/最小值/均值**
- 若最大值超过均值 2 倍，标注为"承接集中"并指出具体负责人名称
- 不对个人工作效率作主观评价

### 三、质量指标解读
- 若有感/升级字段无数据，说明原因并跳过此节
- 有感率和升级率的绝对值
- 有感率最高的产品（列出 Top 3）及其具体数值，若某产品有感率 >20% 标注为"质量风险产品"

{trend_analysis_req}

{forecast_req}

### 六、风险项（Top 3）
每条风险格式：**[风险等级: 高/中/低]** 风险描述 → 建议行动

### 七、改进建议（Top 3）
聚焦流程优化和数据质量，不针对个人，每条格式：
- **[优先级: P1/P2/P3]** 建议内容（预期收益）

---

输出语言：中文，技术性报告风格，简洁精准，避免"高效""优秀"等主观形容词。
"""
        return prompt
    
    def _prepare_resource_prompt(
        self,
        overview: Dict,
        analysis_data: Dict
    ) -> str:
        """准备资源分析的提示词"""
        
        total_cards = overview.get('总卡片数', 0)
        product_dist = overview.get('product_distribution', [])
        
        product_summary = ""
        if product_dist:
            top_products = product_dist[:5]
            product_summary = "主要产品分布：\n"
            for prod in top_products:
                product_summary += f"- {prod['name']}: {prod['value']} 项 ({prod['percentage']})\n"
        
        prompt = f"""
请对以下资源分析数据进行专业的 AI 解读：

【数据概览】
- 总资源数：{total_cards}

【产品分布】
{product_summary}

请从以下几个方面进行分析：
1. 资源分布特点和规律
2. 主要产品的资源占比分析
3. 资源利用效率评估
4. 潜在的资源瓶颈
5. 资源优化建议

请用简洁、专业的语言进行解读。
"""
        return prompt
    
    def _prepare_monitoring_prompt(
        self,
        report_type: str,
        overview: Dict,
        analysis_data: Dict
    ) -> str:
        """准备监控分析的提示词"""
        
        report_name = "BCC 监控" if report_type == "bcc_monitoring" else "BOS 监控"
        total_items = overview.get('总卡片数', 0)
        
        prompt = f"""
请对以下 {report_name} 数据进行专业的 AI 解读：

【监控概览】
- 监控项总数：{total_items}
- 数据时间：{overview.get('数据时间', '最近')}

请从以下几个方面进行分析：
1. 监控数据的整体健康状况
2. 主要的异常和告警情况
3. 性能指标的趋势分析
4. 潜在的风险和隐患
5. 优化和改进建议

请用简洁、专业的语言进行解读，重点突出关键告警和风险。
"""
        return prompt
    
    def _prepare_generic_prompt(
        self,
        report_type: str,
        analysis_data: Dict
    ) -> str:
        """准备通用提示词"""
        
        data_summary = json.dumps(analysis_data, ensure_ascii=False, indent=2)[:1000]  # 限制长度
        
        prompt = f"""
请对以下 {report_type} 分析数据进行专业的 AI 解读：

【数据摘要】
{data_summary}

请从以下几个方面进行分析：
1. 数据的主要特点和规律
2. 关键指标的评估
3. 存在的问题和瓶颈
4. 改进建议

请用简洁、专业的语言进行解读。
"""
        return prompt
    
    def _format_as_html(self, text: str) -> str:
        """
        将文本格式化为 HTML
        
        Args:
            text: 纯文本内容
        
        Returns:
            str: HTML 格式的内容
        """
        # 转义 HTML 特殊字符
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # 处理换行和段落
        lines = text.split('\n')
        html_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题（以数字开头或特殊符号）
            if line and (line[0].isdigit() or line.startswith('【') or line.startswith('【')):
                html_lines.append(f'<h4>{line}</h4>')
            # 检测列表项
            elif line.startswith('-') or line.startswith('•'):
                html_lines.append(f'<li>{line[1:].strip()}</li>')
            else:
                html_lines.append(f'<p>{line}</p>')
        
        # 合并相邻的列表项
        html_content = '\n'.join(html_lines)
        html_content = html_content.replace('</li>\n<li>', '</li>\n<li>')
        
        # 包装列表
        import re
        html_content = re.sub(
            r'(<li>.*?</li>)',
            lambda m: f'<ul>{m.group(1)}</ul>' if not m.group(0).startswith('<ul>') else m.group(0),
            html_content,
            flags=re.DOTALL
        )
        
        return html_content


# 无 db 时的全局单例（兼容旧调用）
_interpreter = None


def get_report_ai_interpreter(db=None) -> ReportAIInterpreter:
    """
    获取报告 AI 解读服务实例

    Args:
        db: SQLAlchemy Session，若传入则从数据库读取 AI 配置；
            不传则走环境变量，并使用全局单例缓存
    """
    global _interpreter

    # 有 db 时每次创建新实例（db session 不可跨请求复用）
    if db is not None:
        return ReportAIInterpreter(db=db)

    # 无 db 时使用全局单例
    if _interpreter is None:
        _interpreter = ReportAIInterpreter()
    return _interpreter
