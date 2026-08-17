---
name: slack-gif-creator
description: 用于创建针对 Slack 优化的动态 GIF 的知识与工具。提供约束条件、校验工具和动画理念。当用户请求为 Slack 制作动态 GIF 时使用，例如"给我做一个 X 在 Slack 里做 Y 的 GIF"。
license: Complete terms in LICENSE.txt
---

# Slack GIF 创建工具

一套用于创建针对 Slack 优化的动画 GIF 的工具包，提供实用工具和相关知识。

## Slack 要求

**尺寸：**
- 表情 GIF：128x128（推荐）
- 消息 GIF：480x480

**参数：**
- FPS：10-30（越低文件越小）
- 颜色数：48-128（越少文件越小）
- 时长：表情 GIF 保持在 3 秒以内

## 核心工作流

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

# 1. 创建 builder
builder = GIFBuilder(width=128, height=128, fps=10)

# 2. 生成帧
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)

    # Draw your animation using PIL primitives
    # (circles, polygons, lines, etc.)

    builder.add_frame(frame)

# 3. 保存并优化
builder.save('output.gif', num_colors=48, optimize_for_emoji=True)
```

## 绘制图形

### 处理用户上传的图片
如果用户上传了图片，考虑他们的意图是：
- **直接使用**（例如"给这个做动画""把这张图拆成帧"）
- **作为灵感参考**（例如"做一个类似这样的东西"）

使用 PIL 加载和处理图片：
```python
from PIL import Image

uploaded = Image.open('file.png')
# Use directly, or just as reference for colors/style
```

### 从零绘制
从零绘制图形时，使用 PIL 的 ImageDraw 基元：

```python
from PIL import ImageDraw

draw = ImageDraw.Draw(frame)

# Circles/ovals
draw.ellipse([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)

# Stars, triangles, any polygon
points = [(x1, y1), (x2, y2), (x3, y3), ...]
draw.polygon(points, fill=(r, g, b), outline=(r, g, b), width=3)

# Lines
draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=5)

# Rectangles
draw.rectangle([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)
```

**不要使用：** 表情字体（跨平台不可靠），也不要假设本技能中存在预打包的图形。

### 让图形好看

图形应显得精致有创意，而非简陋。做法如下：

**使用更粗的线条** - 轮廓和线条始终设置 `width=2` 或更高。细线（width=1）会显得断续且业余。

**增加视觉层次**：
- 背景使用渐变（`create_gradient_background`）
- 叠加多个形状以增加复杂度（例如一个星星里套一个更小的星星）

**让形状更有趣**：
- 不要只画一个普通圆圈——添加高光、环形或图案
- 星星可以加辉光（在其后方绘制更大、半透明的版本）
- 组合多个形状（星星 + 闪光、圆圈 + 环形）

**注意配色**：
- 使用鲜艳、互补的颜色
- 增加对比（浅色形状用深色轮廓，深色形状用浅色轮廓）
- 考虑整体构图

**对于复杂形状**（心形、雪花等）：
- 使用多边形和椭圆的组合
- 精心计算点位以保持对称
- 添加细节（心形可以有一道高光曲线，雪花有精致的分支）

发挥创意、注重细节！一个好的 Slack GIF 应当显得精致，而不像占位图形。

## 可用工具

### GIFBuilder (`core.gif_builder`)
组装帧并针对 Slack 优化：
```python
builder = GIFBuilder(width=128, height=128, fps=10)
builder.add_frame(frame)  # Add PIL Image
builder.add_frames(frames)  # Add list of frames
builder.save('out.gif', num_colors=48, optimize_for_emoji=True, remove_duplicates=True)
```

### 校验器 (`core.validators`)
检查 GIF 是否满足 Slack 要求：
```python
from core.validators import validate_gif, is_slack_ready

# Detailed validation
passes, info = validate_gif('my.gif', is_emoji=True, verbose=True)

# Quick check
if is_slack_ready('my.gif'):
    print("Ready!")
```

### 缓动函数 (`core.easing`)
让运动平滑而非线性：
```python
from core.easing import interpolate

# Progress from 0.0 to 1.0
t = i / (num_frames - 1)

# Apply easing
y = interpolate(start=0, end=400, t=t, easing='ease_out')

# Available: linear, ease_in, ease_out, ease_in_out,
#           bounce_out, elastic_out, back_out
```

### 帧辅助函数 (`core.frame_composer`)
针对常见需求的便捷函数：
```python
from core.frame_composer import (
    create_blank_frame,         # Solid color background
    create_gradient_background,  # Vertical gradient
    draw_circle,                # Helper for circles
    draw_text,                  # Simple text rendering
    draw_star                   # 5-pointed star
)
```

## 动画概念

### 抖动/震动
通过振荡偏移物体位置：
- 用 `math.sin()` 或 `math.cos()` 配合帧索引
- 加入小幅随机变化以获得自然感
- 应用到 x 和/或 y 位置

### 脉动/心跳
有节奏地缩放物体大小：
- 用 `math.sin(t * frequency * 2 * math.pi)` 实现平滑脉动
- 心跳效果：两次快速脉动后暂停（调整正弦波）
- 在基础尺寸的 0.8 到 1.2 之间缩放

### 弹跳
物体下落并弹起：
- 落地用 `interpolate()` 配合 `easing='bounce_out'`
- 下落（加速）用 `easing='ease_in'`
- 每帧增加 y 方向速度以模拟重力

### 旋转
物体绕中心旋转：
- PIL：`image.rotate(angle, resample=Image.BICUBIC)`
- 摇摆效果：用正弦波取代线性角度

### 淡入/淡出
逐渐出现或消失：
- 创建 RGBA 图像，调整 alpha 通道
- 或使用 `Image.blend(image1, image2, alpha)`
- 淡入：alpha 从 0 到 1
- 淡出：alpha 从 1 到 0

### 滑入
将物体从屏幕外移动到目标位置：
- 起始位置：帧边界之外
- 结束位置：目标位置
- 用 `interpolate()` 配合 `easing='ease_out'` 实现平滑停止
- 若要过冲：使用 `easing='back_out'`

### 缩放
为缩放效果调整比例和位置：
- 放大：比例从 0.1 到 2.0，居中裁剪
- 缩小：比例从 2.0 到 1.0
- 可加运动模糊增强戏剧效果（PIL 滤镜）

### 爆炸/粒子迸发
创建向外辐射的粒子：
- 生成具有随机角度和速度的粒子
- 更新每个粒子：`x += vx`、`y += vy`
- 加重力：`vy += gravity_constant`
- 随时间淡出粒子（降低 alpha）

## 优化策略

仅在被要求缩小文件体积时，采用以下部分方法：

1. **减少帧数** - 降低 FPS（用 10 代替 20）或缩短时长
2. **减少颜色** - 用 `num_colors=48` 代替 128
3. **缩小尺寸** - 用 128x128 代替 480x480
4. **移除重复帧** - 在 save() 中设 `remove_duplicates=True`
5. **表情模式** - `optimize_for_emoji=True` 自动优化

```python
# Maximum optimization for emoji
builder.save(
    'emoji.gif',
    num_colors=48,
    optimize_for_emoji=True,
    remove_duplicates=True
)
```

## 理念

本技能提供：
- **知识**：Slack 的要求和动画概念
- **工具**：GIFBuilder、校验器、缓动函数
- **灵活性**：使用 PIL 基元自行编写动画逻辑

它不提供：
- 死板的动画模板或预制函数
- 表情字体渲染（跨平台不可靠）
- 内置于技能中的预打包图形库

**关于用户上传的说明**：本技能不包含预制图形，但如果用户上传了图片，请用 PIL 加载并处理它——根据其请求判断他们是想直接使用还是仅作灵感参考。

发挥创意！组合各种概念（弹跳 + 旋转、脉动 + 滑入等），充分利用 PIL 的全部能力。

## 依赖项

```bash
pip install pillow imageio numpy
```
