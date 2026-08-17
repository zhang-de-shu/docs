---
name: video-ppt
description: 数字人PPT讲解视频生成。支持两种模式：(1) 从原始文档自动生成PPT和台词并生成视频；(2) 直接指定已有PPT和台词文件生成视频。最终效果为左右拼接布局，数字人(9:16)在左侧占1/4宽度，PPT幻灯片在右侧占3/4宽度。
---

# 前置条件

使用前需设置环境变量 `VIDEO_GEN_API_KEY`，用于调用视频生成模型，值为 AI 平台的 Bearer Token：

```bash
export VIDEO_GEN_API_KEY='Bearer eyJhbGci...'
```

# step0: 确定输入模式

根据用户提供的内容判断最可能的模式，**向用户说明后续流程并确认**：

**模式A：从原始文档生成（推荐）**
- 用户提供原始文档（网页、本地文件等）
- 说明：将依次 ① 生成PPT ② 生成台词 ③ 生成视频，询问用户是否确定，或是否需要自行提供PPT/台词
- 确认后进入 step1

**模式B：直接指定PPT和台词**
- 用户已有PPT和台词JSON文件
- 说明：将直接使用已有PPT和台词生成视频，询问用户是否确定
- 确认后跳到 step4

**模式C：仅指定PPT，需生成台词**
- 用户已有PPT但没有台词
- 说明：将根据PPT内容生成台词后生成视频，询问用户是否确定，以及是否有原始文档可辅助台词生成
- 确认后跳到 step3


# step1: 读取原始内容

- 读取用户指定内容
    - 如指定网站或者要求从当前网页读取，则使用chrome_mcp_server或者其他浏览器mcp或者在线文档读取mcp进行读取内容（按顺序依次尝试）
    - 如指定本地文件地址则直接读取内容
    - 文件或文档名作为标题


# step2: 生成PPT

- 使用 `/frontend-slides` skill 基于原始内容生成一份精美的HTML演示文稿
- **首先确定本次工作目录**：使用当前时间生成文件夹 `.claude/skills/video-ppt/temp/{yyyyMMdd_HHmmss}/`，后续所有步骤的文件都保存在此目录下（同一次调用必须使用同一个文件夹）
- PPT文件保存到：`{工作目录}/ppt.html`
- 生成完成后，记录PPT的总页数和每页的核心内容摘要（用于后续台词生成）
- 十分重要：记住每页PPT的主题和要点，后续台词必须与之一一对应
- 十分重要：生成PPT之后需要用户确认内容后才可继续


# step3: 生成台词（PPT对齐）

- 核心原则：**台词必须与PPT页码严格一一对应，每页PPT对应一段台词，台词不得跨页**
- 台词文件保存到：`{工作目录}/scripts.json`（与step2的PPT在同一个文件夹）

## 台词生成规则

1. 先通览PPT每页内容，结合原始文档（模式A）或仅PPT内容（模式C）提取每页的核心讲解要点
    - **模式A特别注意**：PPT对原始内容做了提炼和精简，信息可能不全或有偏差。台词应以原始文档为信息权威来源，PPT页面仅作为结构骨架，确保讲解内容的准确性和完整性
2. 为每页PPT生成讲解台词（一页PPT可对应一段或多段台词）：
    - 深入浅出，通俗易懂
    - 台词只讲解对应页面的内容，**绝对不能跨页**
    - 每段台词长度控制在 40~85 字（符号不计入），尽量接近上限85字
    - 内容丰富的页面可拆分为多段台词，每段都标注相同的page编号
3. 对于每一句中要突出的重点词汇，用 **xx** 方式加粗（不是必须每句都要有）

## 台词分段规则

- 在，。？!等符号处切分，绝对禁止从词语中间切断（如"智/能"、"服/务"），必须保持每个词的完整性
    ```json
    [
        {"page": 0, "segment": 0, "content": "标题"},
        {"page": 1, "segment": 1, "content": "第1页PPT台词第1段"},
        {"page": 1, "segment": 2, "content": "第1页PPT台词第2段"},
        {"page": 2, "segment": 3, "content": "第2页PPT台词（仅1段）"},
        {"page": 3, "segment": 4, "content": "第3页PPT台词第1段"},
        {"page": 3, "segment": 5, "content": "第3页PPT台词第2段"}
    ]
    ```
- page: PPT分页序号(序号从1开始，0用来和segment0对应，content值为文档标题)
- segment: 台词分段序号，全局递增（0为标题，1开始为正文）
- content: 台词内容
- 同一page可出现多次（多段台词），segment全局唯一递增
- **检查：每个PPT页面至少有一段台词，且不存在PPT中没有的page编号**
- **模式B**情况下，需要先检查台词中是否存在错字和漏字并修正

## 最终回顾
- 是否每段台词接近85字，如果拆分过细，需要将段的台词段合并
- 台词是是否是对应PPT页面的讲解，务必准确对应
- 台词生成完成后需要用户确认才可继续


# step4: 视频生成

## 4.1 处理虚拟人图片

如果用户提供了自定义虚拟人图片，先转换为 9:16 竖版肖像图：
`python ./scripts/portrait.py <用户提供的图片> -o assets/avatar_tmp.png`
然后在 step4.2 中使用 `--avatars assets/avatar_tmp.png`。

## 4.2 处理参考音频

如果用户提供了自定义参考音频（任意格式），先转换为 WAV：
`python ./scripts/audio_convert.py <用户提供的音频> -o assets/voice_tmp.wav`
然后在 step4.3 中使用 `--voice assets/voice_tmp.wav`。

## 4.3 生成视频

- 执行 `python ./scripts/video_gen.py --script xxx --ppt xxx`
- 如果提示找不到依赖模块，先加载 shell 环境再执行（macOS/Linux: 添加 `source ~/.zshrc &&` 前缀）
- 后台执行即可，脚本耗时较久，无需等待结果
- 参数说明：
    - script xxx   台词脚本路径(str)
    - ppt xxx  PPT/PPTX/PDF/HTML文件路径(str)
    - avatars xxx   虚拟人初始图片(str, 默认:assets/avatars.png)
    - voice xxx  参考音频文件(str, 默认:assets/大家好欢迎来到一分钟学产品.wav)
    - subtitle xxx   是否烧录字幕(bool, 默认:True)
    - silence xxx  是否截断尾部静音(bool, 默认:True)
    - title xxx  是否添加标题卡(bool, 默认:True)
