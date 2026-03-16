# UI/UX Pro Max 快捷命令

在项目根目录下添加以下别名到 `~/.zshrc` 或 `~/.bashrc`：

```bash
# UI/UX Pro Max 搜索工具
alias uisearch='python3 $PWD/scripts/ui_search.py'
```

或者在项目内创建快捷脚本：

```bash
# 创建快捷命令
cat > uisearch << 'EOF'
#!/bin/bash
python3 "$(dirname "$0")/scripts/ui_search.py" "$@"
EOF
chmod +x uisearch
```

然后就可以直接使用：
```bash
./uisearch "dashboard monitoring" --domain product
./uisearch "button hover" --stack vue
./uisearch "glassmorphism" --domain style
```
