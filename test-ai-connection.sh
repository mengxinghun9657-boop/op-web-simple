#!/bin/bash

# AI 服务连接测试脚本
# 用于验证内网环境是否能连接到 AI 服务

echo "╔══════════════════════════════════════════╗"
echo "║     AI 服务连接测试                      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 从 .env 读取配置
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | grep -v '^[[:space:]]*$' | xargs)
    echo "✓ 已加载 .env 配置"
else
    echo "❌ 未找到 .env 文件"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "配置信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ERNIE API URL: $ERNIE_API_URL"
echo "ERNIE Model: $ERNIE_MODEL"
echo "Embedding API URL: $EMBEDDING_API_URL"
echo ""

# 测试 1: ERNIE API 连接测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 1: ERNIE API 连接测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "目标: $ERNIE_API_URL"
echo ""

# 测试基本连接
echo "1.1 测试基本连接（curl）..."
if curl -s --connect-timeout 5 --max-time 10 "$ERNIE_API_URL" > /dev/null 2>&1; then
    echo "✓ 连接成功"
else
    echo "❌ 连接失败"
    echo ""
    echo "详细错误信息:"
    curl -v --connect-timeout 5 --max-time 10 "$ERNIE_API_URL" 2>&1 | tail -20
fi

echo ""
echo "1.2 测试 API 调用（带认证）..."
ERNIE_RESPONSE=$(curl -s --connect-timeout 10 --max-time 30 \
    -X POST "$ERNIE_API_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ERNIE_API_KEY" \
    -d '{
        "model": "'"$ERNIE_MODEL"'",
        "messages": [
            {"role": "user", "content": "你好"}
        ],
        "temperature": 0.7
    }' 2>&1)

if echo "$ERNIE_RESPONSE" | grep -q "choices\|content"; then
    echo "✓ API 调用成功"
    echo ""
    echo "响应示例:"
    echo "$ERNIE_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
else
    echo "❌ API 调用失败"
    echo ""
    echo "响应内容:"
    echo "$ERNIE_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 2: Embedding API 连接测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "目标: $EMBEDDING_API_URL"
echo ""

# 测试基本连接
echo "2.1 测试基本连接（curl）..."
if curl -s --connect-timeout 5 --max-time 10 "$EMBEDDING_API_URL" > /dev/null 2>&1; then
    echo "✓ 连接成功"
else
    echo "❌ 连接失败"
    echo ""
    echo "详细错误信息:"
    curl -v --connect-timeout 5 --max-time 10 "$EMBEDDING_API_URL" 2>&1 | tail -20
fi

echo ""
echo "2.2 测试 API 调用..."
EMBEDDING_RESPONSE=$(curl -s --connect-timeout 10 --max-time 30 \
    -X POST "$EMBEDDING_API_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "texts": ["测试文本"]
    }' 2>&1)

if echo "$EMBEDDING_RESPONSE" | grep -q "embeddings\|success"; then
    echo "✓ API 调用成功"
    echo ""
    echo "响应示例:"
    echo "$EMBEDDING_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20
else
    echo "❌ API 调用失败"
    echo ""
    echo "响应内容:"
    echo "$EMBEDDING_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试 3: 网络诊断"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 提取主机和端口
ERNIE_HOST=$(echo "$ERNIE_API_URL" | sed -E 's|https?://([^:/]+).*|\1|')
ERNIE_PORT=$(echo "$ERNIE_API_URL" | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
if [ "$ERNIE_PORT" = "$ERNIE_API_URL" ]; then
    ERNIE_PORT=80
fi

EMBEDDING_HOST=$(echo "$EMBEDDING_API_URL" | sed -E 's|https?://([^:/]+).*|\1|')
EMBEDDING_PORT=$(echo "$EMBEDDING_API_URL" | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')
if [ "$EMBEDDING_PORT" = "$EMBEDDING_API_URL" ]; then
    EMBEDDING_PORT=80
fi

echo "3.1 DNS 解析测试..."
echo "ERNIE Host: $ERNIE_HOST"
if host "$ERNIE_HOST" > /dev/null 2>&1; then
    echo "✓ DNS 解析成功"
    host "$ERNIE_HOST"
else
    echo "❌ DNS 解析失败"
fi

echo ""
echo "Embedding Host: $EMBEDDING_HOST"
if host "$EMBEDDING_HOST" > /dev/null 2>&1; then
    echo "✓ DNS 解析成功"
    host "$EMBEDDING_HOST"
else
    echo "❌ DNS 解析失败"
fi

echo ""
echo "3.2 端口连通性测试..."
echo "ERNIE: $ERNIE_HOST:$ERNIE_PORT"
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$ERNIE_HOST/$ERNIE_PORT" 2>/dev/null; then
    echo "✓ 端口可达"
else
    echo "❌ 端口不可达"
fi

echo ""
echo "Embedding: $EMBEDDING_HOST:$EMBEDDING_PORT"
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$EMBEDDING_HOST/$EMBEDDING_PORT" 2>/dev/null; then
    echo "✓ 端口可达"
else
    echo "❌ 端口不可达"
fi

echo ""
echo "3.3 Ping 测试..."
echo "ERNIE Host: $ERNIE_HOST"
if ping -c 3 -W 2 "$ERNIE_HOST" > /dev/null 2>&1; then
    echo "✓ Ping 成功"
    ping -c 3 "$ERNIE_HOST" | tail -2
else
    echo "❌ Ping 失败（可能被防火墙阻止，不影响 HTTP 连接）"
fi

echo ""
echo "Embedding Host: $EMBEDDING_HOST"
if ping -c 3 -W 2 "$EMBEDDING_HOST" > /dev/null 2>&1; then
    echo "✓ Ping 成功"
    ping -c 3 "$EMBEDDING_HOST" | tail -2
else
    echo "❌ Ping 失败（可能被防火墙阻止，不影响 HTTP 连接）"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "测试总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "如果所有测试都失败，可能的原因："
echo "1. 内网环境无法访问外网 AI 服务"
echo "2. 防火墙阻止了连接"
echo "3. AI 服务地址配置错误"
echo "4. AI 服务暂时不可用"
echo ""
echo "建议："
echo "- 确认内网是否有访问外网的权限"
echo "- 检查防火墙规则"
echo "- 联系网络管理员确认网络策略"
echo ""
