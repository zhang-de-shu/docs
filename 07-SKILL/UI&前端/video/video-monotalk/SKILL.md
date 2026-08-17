---
name: video-monotalk
description: 数字人视频生成流程。基于台词脚本（JSON）自动生成数字人讲解视频，支持首帧驱动、字幕烧录（含艺术字标记）、抠图换背景、声色替换、静音截断等全流程。适用于产品介绍、培训讲解等短视频批量生成场景。
---


# step0: 确定工作目录

- **首先确定本次工作目录**：使用当前时间生成文件夹 `.claude/skills/video-monotalk/temp/{yyyyMMdd_HHmmss}/`，后续所有步骤的文件都保存在此目录下（同一次调用必须使用同一个文件夹）

# step1:台词生成
- 读取用户指定内容
    - 如指定网站或者要求从当前网页读取，则使用chrome_mcp_server或者其他浏览器mcp或者在线文档读取mcp进行读取内容（按顺序依次尝试）
    - 如指定本地文件地址则直接读取内容
    - 文件或文档名作为标题
- 生成一份深入浅出，通俗易懂的讲解台词，需包含所有**核心讲解要点**
    - 用户如说明无需生成或者已经是台词，则无需生成，改为检查是否存在错字和漏字并修正，然后直接作为台词使用
- 对于每一句中要突出的中重点词汇，用**xx*方式加粗（不是必须每句都要有）

# step2:台词分段
- 十分重要：将台词分段（无需依据语义,也不要使用脚本切分），要求每段**尽可能长**，尽量接近80字上限（符号不计入字数统计）
- 在，。？!等符号处切分，绝对禁止从词语中间切断（如"智/能"、"服/务"），必须保持每个词的完整性
- 保存为json文件到 `{工作目录}/scripts.json`，格式如下：
    [
        {'page':0, 'content': '标题'}
        {'page':1, 'content': 'xxx'},
        {'page':2, 'content': 'xxx'}
    ]
- page0为文档标题，无标题则生成一个标题

# step3:视频生成
- 执行 `python ./scripts/video_gen.py --script xxx`
- 如果提示找不到依赖模块，先加载 shell 环境再执行（macOS/Linux: 添加 `source ~/.zshrc &&` 前缀）
- 后台执行即可，脚本耗时较久，无需等待结果
- 参数说明：
    - script xxx   台词脚本路径(str)
    - avatars xxx   虚拟人初始图片(str, 默认:assets/avatars.png)
    - voice xxx  参考音频文件(str, 默认:assets/大家好欢迎来到一分钟学产品.wav)
    - subtitle xxx   是否烧录字幕(bool, 默认:True)
    - silence xxx  是否截断尾部静音(bool, 默认:True)
    - title xxx  是否添加标题卡(bool, 默认:True)
    


