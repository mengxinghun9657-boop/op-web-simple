#!/bin/bash
# 检查webhook配置

echo "🔍 检查webhook配置..."

docker compose -f docker-compose.prod.yml exec -T mysql mysql -u root -p'Zhang~~1' cluster_management << 'EOF'
SELECT 
    id, 
    name, 
    type, 
    enabled,
    severity_filter,
    component_filter,
    SUBSTRING(url, 1, 50) as url_preview
FROM webhook_configs
ORDER BY id;
EOF

echo ""
echo "💡 如果没有启用的webhook配置，需要在前端添加"
