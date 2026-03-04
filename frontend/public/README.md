# 网页图标说明

## 当前图标

- `favicon.svg` - SVG格式图标（现代浏览器支持，矢量图标，清晰度最佳）

## 生成ICO格式图标（可选）

如果需要支持旧版浏览器，可以生成ICO格式：

### 方法1：在线转换
1. 访问 https://www.favicon-generator.org/
2. 上传 `favicon.svg` 文件
3. 下载生成的 `favicon.ico`
4. 放到 `frontend/public/` 目录

### 方法2：使用ImageMagick
```bash
# 安装ImageMagick
brew install imagemagick  # macOS

# 转换SVG为ICO
convert favicon.svg -resize 32x32 favicon.ico
```

### 方法3：使用在线工具
- https://realfavicongenerator.net/
- https://favicon.io/

## 图标设计说明

当前图标设计元素：
- 蓝色渐变背景：代表云计算
- 白色云朵：云资源
- 服务器图标：运维分析
- 绿色指示灯：系统运行状态
