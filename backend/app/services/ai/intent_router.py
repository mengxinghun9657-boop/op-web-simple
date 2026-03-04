#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
意图路由器（Intent Router）

实现需求：
- Requirements 2.1: 实现意图分类（sql/rag_report/rag_knowledge/chat/mixed）
- Requirements 2.2: 调用 ERNIE API 进行意图分类
- Requirements 2.3: 语义相似度辅助判断（置信度 < 0.7）
- Requirements 2.7: 加载典型问题库
- Requirements 2.8: 关键词规则降级路由（置信度 < 0.5）
- Requirements 2.4: 识别混合查询
"""

import json
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from app.core.logger import logger
from app.services.ai.ernie_client import ERNIEClient
from app.services.ai.embedding_model import EmbeddingModel
from app.services.ai.query_preprocessor import QueryPreprocessor
from app.services.ai.cost_optimizer import CostOptimizer
from app.services.ai.query_rewriter import QueryRewriter
from app.services.ai.anomaly_detector import AnomalyDetector


class IntentRouter:
    """意图路由器"""
    
    # 意图类型定义
    INTENT_SQL = "sql"  # SQL 查询
    INTENT_RAG_REPORT = "rag_report"  # 报告检索
    INTENT_RAG_KNOWLEDGE = "rag_knowledge"  # 知识库检索
    INTENT_CHAT = "chat"  # 闲聊对话
    INTENT_MIXED = "mixed"  # 混合查询
    
    def __init__(
        self,
        ernie_client: Optional[ERNIEClient] = None,
        embedding_model: Optional[EmbeddingModel] = None,
        routing_rule_manager: Optional['RoutingRuleManager'] = None,
        query_preprocessor: Optional[QueryPreprocessor] = None,
        cost_optimizer: Optional[CostOptimizer] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        anomaly_detector: Optional[AnomalyDetector] = None
    ):
        """
        初始化意图路由器
        
        Args:
            ernie_client: ERNIE API 客户端
            embedding_model: Embedding 模型
            routing_rule_manager: 路由规则管理器
            query_preprocessor: 查询预处理器
            cost_optimizer: 成本优化器
            query_rewriter: 查询改写器
            anomaly_detector: 异常检测器
        """
        self.ernie_client = ernie_client or ERNIEClient()
        self.embedding_model = embedding_model or EmbeddingModel()
        self.routing_rule_manager = routing_rule_manager  # 延迟初始化
        self.query_preprocessor = query_preprocessor or QueryPreprocessor()
        self.cost_optimizer = cost_optimizer or CostOptimizer()
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        
        # 加载典型问题库
        # Requirements 2.7: 加载典型问题库（50+ 示例）
        self.typical_questions = self._load_typical_questions()
        
        # 预计算典型问题的向量
        self.typical_question_embeddings = {}
        # 注意：_precompute_embeddings 现在是 async，需要在使用前调用
        # 在实际使用时会延迟初始化
        
        # 编译并缓存正则表达式（性能优化）
        # Task 19.1: 实现强制规则缓存
        import re
        self._ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self._instance_id_pattern = re.compile(
            r'(^|[^a-zA-Z0-9])(i-[a-zA-Z0-9]+|instance-[a-zA-Z0-9]+|ins-[a-zA-Z0-9]+)($|[^a-zA-Z0-9])',
            re.IGNORECASE
        )
        
        # 关键词规则
        # Requirements 2.8: 关键词规则降级路由
        self.keyword_rules = {
            self.INTENT_SQL: [
                # 查询类关键词
                "查询", "统计", "多少", "有哪些", "列出", "显示",
                "数量", "总数", "平均", "最大", "最小", "求和",
                "SELECT", "COUNT", "SUM", "AVG", "MAX", "MIN",
                # 统计关键词（新增）
                "汇总", "合计", "计算", "占比", "百分比", "排名",
                "TOP", "前", "后", "排序", "分组", "GROUP BY",
                # IP地址、实例ID、集群相关查询
                "属于", "所属", "集群", "实例", "服务器", "节点",
                "IP", "ip", "地址", "主机", "机器", "设备"
            ],
            self.INTENT_RAG_REPORT: [
                # 报告检索关键词
                "报告", "分析结果", "上次分析", "最近的报告", "报告内容",
                "分析报告", "监控报告", "资源报告", "运营报告",
                # 新增报告关键词
                "上次", "上一次", "最新", "历史", "之前的",
                "昨天", "上周", "上个月", "最近一次"
            ],
            self.INTENT_RAG_KNOWLEDGE: [
                "如何", "怎么", "什么是", "介绍", "说明", "帮助",
                "文档", "教程", "指南", "知识"
            ],
            self.INTENT_CHAT: [
                "你好", "谢谢", "再见", "帮我", "能不能",
                "可以吗", "行吗", "好的", "明白"
            ]
        }
        
        logger.info("✅ 意图路由器初始化成功")
    
    def _load_typical_questions(self) -> Dict[str, List[str]]:
        """
        加载典型问题库
        
        Returns:
            典型问题字典 {intent_type: [questions]}
        
        Validates: Requirements 2.7
        """
        # 典型问题库（80+ 示例）
        typical_questions = {
            self.INTENT_SQL: [
                # 数据查询类（40 个）
                "查询所有用户信息",
                "统计活跃用户数量",
                "列出最近一周的订单",
                "显示销售额最高的产品",
                "有多少个集群",
                "查询状态为运行中的实例",
                "统计每个区域的服务器数量",
                "列出 CPU 使用率超过 80% 的服务器",
                "查询内存使用量最大的 10 个实例",
                "显示今天创建的任务",
                "统计各个状态的任务数量",
                "查询失败的任务列表",
                "列出所有 BCC 实例",
                "显示 BOS 存储桶信息",
                "查询 EIP 使用情况",
                "统计集群健康状态分布",
                "列出异常的监控指标",
                "查询资源使用趋势",
                "显示成本最高的资源",
                "统计各类型资源的数量",
                # IP地址查询（10个）
                "10.90.0.245 属于哪个集群",
                "查询 192.168.1.100 所属的集群",
                "IP 地址 10.90.0.140 在哪个集群",
                "节点 10.0.0.50 的配置信息",
                "172.16.0.1 是哪台服务器",
                "IP 地址 8.8.8.8 的详细信息",
                "查询 10.10.10.10 的实例信息",
                "192.168.0.1 属于哪个节点",
                "这个 IP 10.20.30.40 的状态",
                "查看 172.31.0.1 的配置",
                # 实例ID查询（10个）
                "实例 i-abc123 的详细信息",
                "查询 instance-xyz789 的状态",
                "ins-test001 在哪个集群",
                "i-prod456 的配置信息",
                "instance-dev789 的资源使用情况",
                "查看 i-staging123 的监控数据",
                "ins-backup001 的备份状态",
                "实例 i-web001 的网络配置",
                "instance-db001 的存储信息",
                "查询 i-cache001 的性能指标",
                # 统计查询（10个）
                "统计所有用户的数量",
                "计算平均响应时间",
                "求和所有订单金额",
                "汇总各区域的资源使用",
                "合计本月的成本",
                "计算资源利用率",
                "统计 TOP 10 高负载服务器",
                "排名前 5 的任务",
                "分组统计各类型实例数量",
                "计算占比最高的资源类型"
            ],
            self.INTENT_RAG_REPORT: [
                # 报告检索类（20 个）
                "最近的资源分析报告",
                "上次监控分析的结果",
                "查看运营分析报告",
                "最新的 BCC 监控报告",
                "上周的 BOS 分析报告",
                "最近一次的集群健康报告",
                "查看昨天的分析结果",
                "最新的异常报告",
                "上个月的资源使用报告",
                "最近的性能分析报告",
                "查看最新的告警报告",
                "上次分析发现了什么问题",
                "最近的报告有哪些建议",
                "查看历史分析报告",
                "最新的趋势分析报告",
                # 新增报告查询（5个）
                "上一次的 GPU 监控报告",
                "最近的成本分析报告",
                "昨天的运维报告",
                "上周的安全审计报告",
                "最新的容量规划报告"
            ],
            self.INTENT_RAG_KNOWLEDGE: [
                # 知识库检索类（15 个）
                "如何创建 BCC 实例",
                "什么是 EIP",
                "BOS 存储桶怎么配置",
                "集群健康检查的标准是什么",
                "如何优化资源使用",
                "监控指标的含义",
                "告警规则如何设置",
                "资源配额限制说明",
                "如何进行故障排查",
                "系统架构介绍",
                # 新增知识查询（5个）
                "如何配置负载均衡",
                "什么是容器编排",
                "怎么设置自动扩缩容",
                "网络安全策略配置方法",
                "数据备份恢复流程"
            ],
            self.INTENT_CHAT: [
                # 闲聊对话类（10 个）
                "你好",
                "谢谢你的帮助",
                "再见",
                "你能做什么",
                "帮我分析一下",
                "好的，明白了",
                "可以帮我吗",
                "非常感谢",
                "辛苦了",
                "收到"
            ]
        }
        
        logger.info(f"✅ 加载典型问题库: {sum(len(v) for v in typical_questions.values())} 个示例")
        return typical_questions
    
    async def _precompute_embeddings(self):
        """预计算典型问题的向量"""
        try:
            for intent_type, questions in self.typical_questions.items():
                self.typical_question_embeddings[intent_type] = []
                for question in questions:
                    embedding = await self.embedding_model.encode(question)
                    self.typical_question_embeddings[intent_type].append(embedding)
            
            logger.info("✅ 典型问题向量预计算完成")
        except Exception as e:
            logger.warning(f"⚠️ 典型问题向量预计算失败: {e}")
            # 降级：不使用语义相似度
            self.typical_question_embeddings = {}
    
    async def route(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[str, float, Optional[List[str]], Optional[Dict], Optional[int], Optional[float], str]:
        """
        路由查询到对应的意图类型
        
        Args:
            query: 用户查询文本
            user_id: 用户ID
            session_id: 会话ID
        
        Returns:
            (intent_type, confidence, handlers, metadata, matched_rule_id, similarity_score, routing_method)
            - intent_type: 意图类型
            - confidence: 置信度 (0-1)
            - handlers: 需要调用的处理器列表（混合查询时返回多个）
            - metadata: 路由规则元数据（如果匹配到规则）
            - matched_rule_id: 匹配的规则 ID（如果有）
            - similarity_score: 相似度分数（如果有）
            - routing_method: 路由方法（forced_rule/routing_rule/ernie/similarity/keyword）
        
        Validates:
            - Requirements 2.1: 实现意图分类
            - Requirements 2.2: 调用 ERNIE API 进行意图分类
            - Requirements 2.3: 语义相似度辅助判断
            - Requirements 2.4: 识别混合查询
            - Requirements 2.8: 关键词规则降级路由
            - Requirements 2.8: 返回规则元数据
            - Requirements 5.1: 记录路由方法和规则匹配信息
        """
        logger.info(f"🔍 意图路由 - query: {query[:50]}...")
        
        # 0. 查询预处理（新增）
        # 参考: 字节跳动RAG 5.1.2节 - 查询理解增强
        preprocess_result = await self.query_preprocessor.preprocess(
            query,
            enable_synonym=True,
            enable_spelling=True,
            enable_entity=True,
            enable_expansion=True
        )
        
        # 使用处理后的查询进行路由
        processed_query = preprocess_result['processed_query']
        entities = preprocess_result['entities']
        
        # 记录预处理信息
        if preprocess_result['changes']:
            logger.info(f"🔧 查询预处理完成: {', '.join(preprocess_result['changes'])}")
            if preprocess_result['corrections']:
                logger.info(f"   纠错: {preprocess_result['corrections']}")
            if entities:
                logger.info(f"   实体: {entities}")
        
        # 0.5 查询改写（新增）
        # 参考: 字节跳动RAG 5.2节 - 查询改写
        rewrite_result = self.query_rewriter.rewrite(
            processed_query,
            enable_decomposition=True,
            enable_completion=True,
            enable_simplification=True
        )
        
        # 记录改写信息
        if rewrite_result['rewrite_applied']:
            logger.info(f"🔧 查询改写完成:")
            if rewrite_result['simplified_query'] != processed_query:
                logger.info(f"   简化: {processed_query} -> {rewrite_result['simplified_query']}")
            if rewrite_result['is_complex']:
                logger.info(f"   分解: {rewrite_result['sub_queries']}")
            if len(rewrite_result['completed_queries']) > 1:
                logger.info(f"   补全: {len(rewrite_result['completed_queries'])} 个变体")
        
        # 使用简化后的查询进行路由
        final_query = rewrite_result['simplified_query']
        
        # 如果是复杂查询(包含多个子查询),需要对每个子查询独立路由
        # 这里暂时使用简化后的查询,后续可以扩展支持多子查询路由
        
        # 1. 检查缓存（成本优化）
        # 参考: 字节跳动RAG 13.2节 - 成本优化
        cached_result = await self.cost_optimizer.get_cached_result(final_query, user_id)
        if cached_result:
            logger.info(f"✅ 使用缓存结果 (命中率: {self.cost_optimizer.get_cache_hit_rate():.2%})")
            return (
                cached_result['intent_type'],
                cached_result['confidence'],
                cached_result['handlers'],
                cached_result.get('metadata'),
                cached_result.get('matched_rule_id'),
                cached_result.get('similarity_score'),
                'cache'  # 路由方法标记为缓存
            )
        
        # 2. 判断是否为简单查询（可以降级，不调用ERNIE）
        # 参考: 字节跳动RAG 13.2节 - 简单查询降级
        is_simple, simple_type = self.cost_optimizer.is_simple_query(final_query)
        if is_simple:
            logger.info(f"✅ 检测到简单查询 ({simple_type})，使用规则引擎降级")
            self.cost_optimizer.record_simple_query()
            
            # 简单查询直接返回SQL意图
            result = {
                'intent_type': self.INTENT_SQL,
                'confidence': 0.95,
                'handlers': [self.INTENT_SQL],
                'metadata': None,
                'matched_rule_id': None,
                'similarity_score': None,
            }
            
            # 缓存结果
            await self.cost_optimizer.set_cached_result(final_query, result, user_id)
            
            return (
                result['intent_type'],
                result['confidence'],
                result['handlers'],
                result['metadata'],
                result['matched_rule_id'],
                result['similarity_score'],
                'simple_query'  # 路由方法标记为简单查询
            )
        
        # 延迟初始化：如果典型问题向量还未计算，先计算
        if not self.typical_question_embeddings and self.typical_questions:
            logger.info("🔄 首次使用，预计算典型问题向量...")
            await self._precompute_embeddings()
        
        # 初始化返回值
        matched_rule_id = None
        similarity_score = None
        routing_method = "ernie"  # 默认路由方法
        
        # 3. 强制规则：检测 IP 地址和实例 ID
        # Task 19.1: 使用缓存的编译正则表达式
        
        # 检测 IP 地址（优先使用实体识别结果）
        if entities.get('ip_addresses') or self._ip_pattern.search(processed_query):
            logger.info(f"✅ 检测到 IP 地址，强制路由到 SQL 查询")
            result = {
                'intent_type': self.INTENT_SQL,
                'confidence': 0.95,
                'handlers': [self.INTENT_SQL],
                'metadata': None,
                'matched_rule_id': None,
                'similarity_score': None,
            }
            # 缓存结果
            await self.cost_optimizer.set_cached_result(processed_query, result, user_id)
            return self.INTENT_SQL, 0.95, [self.INTENT_SQL], None, None, None, "forced_rule"
        
        # 检测实例 ID (i-xxx, instance-xxx, ins-xxx)
        if entities.get('instance_ids') or self._instance_id_pattern.search(processed_query):
            logger.info(f"✅ 检测到实例 ID，强制路由到 SQL 查询")
            result = {
                'intent_type': self.INTENT_SQL,
                'confidence': 0.95,
                'handlers': [self.INTENT_SQL],
                'metadata': None,
                'matched_rule_id': None,
                'similarity_score': None,
            }
            # 缓存结果
            await self.cost_optimizer.set_cached_result(processed_query, result, user_id)
            return self.INTENT_SQL, 0.95, [self.INTENT_SQL], None, None, None, "forced_rule"
        
        # 4. 检查路由规则知识库（使用处理后的查询）
        # Requirements 2.3, 2.4: 检索路由规则知识库
        rule_result = await self._check_routing_rules(processed_query)
        if rule_result:
            intent_type, confidence, metadata, matched_rule_id, similarity_score = rule_result
            routing_method = "routing_rule"
            handlers = self._detect_mixed_query(processed_query, intent_type)
            if len(handlers) > 1:
                intent_type = self.INTENT_MIXED
            logger.info(f"✅ 匹配到路由规则: {intent_type} (置信度: {confidence:.2f})")
            
            # 缓存结果
            result = {
                'intent_type': intent_type,
                'confidence': confidence,
                'handlers': handlers,
                'metadata': metadata,
                'matched_rule_id': matched_rule_id,
                'similarity_score': similarity_score,
            }
            await self.cost_optimizer.set_cached_result(processed_query, result, user_id)
            
            return intent_type, confidence, handlers, metadata, matched_rule_id, similarity_score, routing_method
        
        # 5. 尝试使用 ERNIE API 进行意图分类（使用处理后的查询）
        # Requirements 2.2: 调用 ERNIE API 进行意图分类
        self.cost_optimizer.record_ernie_call()  # 记录ERNIE调用
        intent_type, confidence = await self._classify_with_ernie(processed_query)
        routing_method = "ernie"
        
        # 6. 如果置信度 < 0.7，使用语义相似度辅助判断
        # Requirements 2.3: 语义相似度辅助判断
        if confidence < 0.7 and self.typical_question_embeddings:
            logger.info(f"⚠️ 置信度较低 ({confidence:.2f})，使用语义相似度辅助判断")
            intent_type_sim, confidence_sim = await self._classify_with_similarity(processed_query)
            
            # 如果语义相似度的置信度更高，使用它
            if confidence_sim > confidence:
                logger.info(f"✅ 使用语义相似度结果: {intent_type_sim} ({confidence_sim:.2f})")
                intent_type = intent_type_sim
                confidence = confidence_sim
                routing_method = "similarity"
        
        # 7. 如果置信度 < 0.5，使用关键词规则降级
        # Requirements 2.8: 关键词规则降级路由
        if confidence < 0.5:
            logger.info(f"⚠️ 置信度过低 ({confidence:.2f})，使用关键词规则降级")
            intent_type_kw, confidence_kw = self._classify_with_keywords(processed_query)
            
            if confidence_kw > confidence:
                logger.info(f"✅ 使用关键词规则结果: {intent_type_kw} ({confidence_kw:.2f})")
                intent_type = intent_type_kw
                confidence = confidence_kw
                routing_method = "keyword"
        
        # 8. 检测混合查询
        # Requirements 2.4: 识别混合查询
        handlers = self._detect_mixed_query(processed_query, intent_type)
        
        if len(handlers) > 1:
            intent_type = self.INTENT_MIXED
            logger.info(f"🔀 检测到混合查询，需要调用: {handlers}")
        
        logger.info(f"✅ 意图路由结果: {intent_type} (置信度: {confidence:.2f}, 方法: {routing_method})")
        
        # 9. 记录路由数据到异常检测系统
        # 参考: 字节跳动RAG 8.2节 - 路由异常检测
        import time
        routing_latency_ms = 0.0  # 这里简化处理，实际应该记录整个路由过程的耗时
        
        self.anomaly_detector.record_routing(
            confidence=confidence,
            routing_method=routing_method,
            latency_ms=routing_latency_ms,
            is_error=False  # 如果路由成功，标记为非错误
        )
        
        # 10. 检测异常（每100个请求检测一次，避免频繁检测）
        if self.anomaly_detector.stats['total_requests'] % 100 == 0:
            anomalies = self.anomaly_detector.detect_anomalies()
            if anomalies:
                logger.warning(f"⚠️ 检测到 {len(anomalies)} 个路由异常:")
                for anomaly in anomalies:
                    logger.warning(
                        f"   - {anomaly['type']}: {anomaly['description']} "
                        f"(严重程度: {anomaly['severity']})"
                    )
                    logger.warning(f"   修复建议: {anomaly['suggestions'][0]}")
        
        # 缓存结果
        result = {
            'intent_type': intent_type,
            'confidence': confidence,
            'handlers': handlers,
            'metadata': None,
            'matched_rule_id': matched_rule_id,
            'similarity_score': similarity_score,
        }
        await self.cost_optimizer.set_cached_result(processed_query, result, user_id)
        
        return intent_type, confidence, handlers, None, matched_rule_id, similarity_score, routing_method
    
    async def _classify_with_ernie(self, query: str) -> Tuple[str, float]:
        """
        使用 ERNIE API 进行意图分类
        
        Args:
            query: 用户查询文本
        
        Returns:
            (intent_type, confidence)
        
        Validates: Requirements 2.2
        """
        try:
            # 构建意图分类 Prompt
            prompt = self._build_intent_prompt(query)
            
            # 调用 ERNIE API
            response = await self.ernie_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # 低温度，更确定的结果
            )
            
            # 解析返回的 JSON 结果
            result = self._parse_intent_response(response)
            
            return result["intent_type"], result["confidence"]
            
        except Exception as e:
            logger.error(f"❌ ERNIE API 意图分类失败: {e}")
            # 降级到关键词匹配
            return self.INTENT_CHAT, 0.3
    
    def _build_intent_prompt(self, query: str) -> str:
        """
        构建意图分类 Prompt
        
        Args:
            query: 用户查询文本
        
        Returns:
            Prompt 文本
        """
        prompt = f"""你是一个智能查询意图分类器。请分析用户的查询意图，并返回 JSON 格式的结果。

意图类型说明：
1. sql: 数据库查询，需要从数据库中查询数据
   - 特征：包含统计、列表、数量、查询等关键词
   - 特征：包含 IP 地址、实例 ID、集群名称等具体标识符
   - 示例："查询所有服务器"、"统计任务数量"、"10.90.0.140 属于哪个集群"

2. rag_report: 报告检索，查询历史分析报告的内容
   - 特征：包含"报告"、"分析结果"、"上次分析"等关键词
   - 特征：查询时间相关的报告（最近、上次、昨天等）
   - 示例："最近的 BCC 监控报告"、"上次分析的结果"

3. rag_knowledge: 知识库检索，查询操作指南、概念说明等知识
   - 特征：包含"如何"、"怎么"、"什么是"等疑问词
   - 特征：查询操作方法、概念解释、配置说明
   - 示例："如何创建 BCC 实例"、"什么是 EIP"

4. chat: 闲聊对话，打招呼、感谢等日常对话
   - 特征：简单的问候、感谢、确认等
   - 示例："你好"、"谢谢"、"明白了"

5. mixed: 混合查询，同时涉及多个数据源
   - 特征：同时包含多种意图的关键词
   - 示例："查询服务器数量并生成报告"

重要分类规则（优先级从高到低）：
1. 如果查询包含 IP 地址（如 10.90.0.140）→ 必须分类为 sql
2. 如果查询包含实例 ID（如 i-abc123, instance-xxx）→ 必须分类为 sql
3. 如果查询是"XX 属于哪个集群"、"查询 XX 的信息"→ 应该分类为 sql
4. 如果查询包含统计关键词（统计、总数、平均、求和）→ 优先分类为 sql
5. 如果查询包含报告关键词（报告、分析结果、上次分析）→ 优先分类为 rag_report
6. 只有查询操作方法、概念解释时才分类为 rag_knowledge

用户查询：{query}

请返回 JSON 格式：
{{
    "intent_type": "sql|rag_report|rag_knowledge|chat|mixed",
    "confidence": 0.0-1.0,
    "reason": "分类理由（简短说明为什么选择这个意图类型）"
}}

只返回 JSON，不要其他内容。"""
        
        return prompt
    
    def _parse_intent_response(self, response: str) -> Dict:
        """
        解析 ERNIE API 返回的意图分类结果
        
        Args:
            response: ERNIE API 返回的文本
        
        Returns:
            解析后的结果字典
        """
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                
                # 验证必需字段
                if "intent_type" in result and "confidence" in result:
                    # 确保 intent_type 有效
                    valid_intents = [
                        self.INTENT_SQL,
                        self.INTENT_RAG_REPORT,
                        self.INTENT_RAG_KNOWLEDGE,
                        self.INTENT_CHAT,
                        self.INTENT_MIXED
                    ]
                    
                    if result["intent_type"] not in valid_intents:
                        result["intent_type"] = self.INTENT_CHAT
                    
                    # 确保 confidence 在 0-1 之间
                    result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
                    
                    return result
            
            # 解析失败，返回默认值
            logger.warning(f"⚠️ 无法解析 ERNIE 响应: {response[:100]}")
            return {"intent_type": self.INTENT_CHAT, "confidence": 0.3}
            
        except Exception as e:
            logger.error(f"❌ 解析意图响应失败: {e}")
            return {"intent_type": self.INTENT_CHAT, "confidence": 0.3}
    
    async def _classify_with_similarity(self, query: str) -> Tuple[str, float]:
        """
        使用语义相似度进行意图分类
        
        Args:
            query: 用户查询文本
        
        Returns:
            (intent_type, confidence)
        
        Validates: Requirements 2.3
        """
        try:
            # 向量化查询
            query_embedding = await self.embedding_model.encode(query)
            
            # 计算与所有典型问题的相似度
            best_intent = self.INTENT_CHAT
            best_similarity = 0.0
            
            for intent_type, embeddings in self.typical_question_embeddings.items():
                for typical_embedding in embeddings:
                    # 计算余弦相似度
                    similarity = EmbeddingModel.cosine_similarity(
                        query_embedding,
                        typical_embedding
                    )
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_intent = intent_type
            
            # 相似度转换为置信度（0.5-1.0 映射到 0.6-0.9）
            confidence = 0.6 + (best_similarity - 0.5) * 0.6 if best_similarity > 0.5 else 0.3
            
            logger.info(f"📊 语义相似度分类: {best_intent} (相似度: {best_similarity:.2f})")
            
            return best_intent, confidence
            
        except Exception as e:
            logger.error(f"❌ 语义相似度分类失败: {e}")
            return self.INTENT_CHAT, 0.3
    
    def _classify_with_keywords(self, query: str) -> Tuple[str, float]:
        """
        使用关键词规则进行意图分类
        
        Args:
            query: 用户查询文本
        
        Returns:
            (intent_type, confidence)
        
        Validates: Requirements 2.8
        """
        query_lower = query.lower()
        
        # 统计每个意图类型匹配的关键词数量
        intent_scores = {}
        
        for intent_type, keywords in self.keyword_rules.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1
            
            if score > 0:
                intent_scores[intent_type] = score
        
        # 选择得分最高的意图
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[best_intent]
            
            # 得分转换为置信度（1-3 个关键词 -> 0.5-0.7）
            confidence = min(0.5 + max_score * 0.1, 0.7)
            
            logger.info(f"🔑 关键词规则分类: {best_intent} (匹配: {max_score} 个关键词)")
            
            return best_intent, confidence
        
        # 没有匹配的关键词，默认为闲聊
        return self.INTENT_CHAT, 0.4
    
    async def _check_routing_rules(self, query: str) -> Optional[Tuple[str, float, Dict, int, float]]:
        """
        检查路由规则知识库（使用 RRF 融合算法）
        
        Args:
            query: 用户查询文本
        
        Returns:
            (intent_type, confidence, metadata, rule_id, similarity_score) 或 None
        
        Validates: Requirements 2.3, 2.4, 2.8, 5.1, 12.2, 12.8
        """
        # 如果没有初始化 routing_rule_manager，跳过
        if not self.routing_rule_manager:
            return None
        
        try:
            import time
            
            # 记录开始时间（用于性能监控）
            start_time = time.time()
            
            # 使用 RRF 融合算法检索匹配的规则
            matched_rules = await self.routing_rule_manager.search_rules_with_rrf(
                query=query,
                similarity_threshold=0.7,
                top_k=1,  # 只取最匹配的一个
                rrf_k=60,  # RRF 常数
                vector_top_k=50,  # 向量检索 top-50
                keyword_top_k=50  # 关键词检索 top-50
            )
            
            # 记录检索时间
            elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if not matched_rules:
                logger.info(f"ℹ️ 未匹配到路由规则 (耗时: {elapsed_time:.2f}ms)")
                return None
            
            # 使用优先级最高的规则
            rule = matched_rules[0]
            
            # 获取相似度分数（可能来自向量检索或 RRF 得分）
            similarity = rule.get('similarity', rule.get('rrf_score', 0.8))
            
            logger.info(
                f"🎯 匹配到路由规则: id={rule['id']}, pattern={rule['pattern']}, "
                f"similarity={similarity:.2f}, rrf_score={rule.get('rrf_score', 0):.4f}, "
                f"耗时={elapsed_time:.2f}ms"
            )
            
            return (
                rule['intent_type'],
                similarity,  # 使用相似度作为置信度
                rule.get('metadata'),  # 返回规则元数据
                rule['id'],  # 返回规则 ID
                similarity  # 返回相似度分数
            )
            
        except Exception as e:
            logger.error(f"❌ 检查路由规则失败: {e}")
            return None
    
    def _detect_mixed_query(self, query: str, primary_intent: str) -> List[str]:
        """
        检测混合查询
        
        Args:
            query: 用户查询文本
            primary_intent: 主要意图类型
        
        Returns:
            需要调用的处理器列表
        
        Validates: Requirements 2.4
        """
        handlers = [primary_intent]
        
        # 检测是否同时涉及多个数据源
        query_lower = query.lower()
        
        # 检测 SQL 查询关键词
        sql_keywords = ["查询", "统计", "多少", "列出", "显示"]
        has_sql = any(kw in query_lower for kw in sql_keywords)
        
        # 检测报告检索关键词
        report_keywords = ["报告", "分析结果", "上次分析", "最近的报告"]
        has_report = any(kw in query_lower for kw in report_keywords)
        
        # 检测知识库检索关键词
        knowledge_keywords = ["如何", "怎么", "什么是", "介绍"]
        has_knowledge = any(kw in query_lower for kw in knowledge_keywords)
        
        # 如果检测到多个数据源，添加到处理器列表
        if has_sql and primary_intent != self.INTENT_SQL:
            handlers.append(self.INTENT_SQL)
        
        if has_report and primary_intent != self.INTENT_RAG_REPORT:
            handlers.append(self.INTENT_RAG_REPORT)
        
        if has_knowledge and primary_intent != self.INTENT_RAG_KNOWLEDGE:
            handlers.append(self.INTENT_RAG_KNOWLEDGE)
        
        return handlers


    def get_anomaly_statistics(self) -> Dict:
        """
        获取异常检测统计数据
        
        Returns:
            异常检测统计数据
        
        参考: 字节跳动RAG 8.2节 - 异常检测和自动修复
        """
        return self.anomaly_detector.get_statistics()
    
    def get_recent_anomalies(
        self,
        limit: int = 10,
        severity: Optional[str] = None,
        anomaly_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的异常记录
        
        Args:
            limit: 返回数量限制
            severity: 严重程度过滤（low/medium/high）
            anomaly_type: 异常类型过滤
        
        Returns:
            异常记录列表
        """
        return self.anomaly_detector.get_recent_anomalies(
            limit=limit,
            severity=severity,
            anomaly_type=anomaly_type
        )


    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """
        获取增强的性能监控统计数据

        聚合所有组件的统计数据:
        - 查询预处理监控
        - 成本监控
        - 查询改写监控
        - 异常检测监控

        Returns:
            增强的统计数据字典

        参考: 字节跳动RAG 8.1节和13.3节 - 性能监控
        """
        statistics = {}

        # 1. 查询预处理统计
        if self.query_preprocessor:
            statistics['query_preprocessing'] = self.query_preprocessor.get_statistics()

        # 2. 成本优化统计
        if self.cost_optimizer:
            statistics['cost_optimization'] = self.cost_optimizer.get_cost_savings()

        # 3. 查询改写统计
        if self.query_rewriter:
            statistics['query_rewriting'] = self.query_rewriter.get_statistics()

        # 4. 异常检测统计
        if self.anomaly_detector:
            statistics['anomaly_detection'] = self.anomaly_detector.get_statistics()

        # 5. 路由器基础统计
        statistics['routing'] = {
            'typical_questions_count': sum(len(v) for v in self.typical_questions.values()),
            'typical_questions_by_intent': {
                intent: len(questions)
                for intent, questions in self.typical_questions.items()
            },
            'keyword_rules_count': sum(len(v) for v in self.keyword_rules.values())
        }

        return statistics



# 全局实例（可选）
_intent_router = None


def get_intent_router(
    ernie_client: Optional[ERNIEClient] = None,
    embedding_model: Optional[EmbeddingModel] = None
) -> IntentRouter:
    """获取意图路由器实例"""
    global _intent_router
    
    if _intent_router is None:
        _intent_router = IntentRouter(ernie_client, embedding_model)
    
    return _intent_router
