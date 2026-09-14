---
name: ifg-story
description: 互动影游剧本创作
---

# 执行步骤

## 1. 接收用户种子
用户可能给一句话、一个场景、或一个开头

## 2. 创建项目输出目录并落盘初始文件
```
<工作目录>/ifg-story-<项目名>/
├── project.json   # 事实来源，按 references/data-model.md 结构，随每阶段产出增量更新
├── images         # 文件夹，后续用
└── 剧本.md         # 阶段四导出
```
- `project.json` 是贯穿全程的**磁盘文件**：每阶段经用户确认的字段立即写入/合并进该文件。
- 后续脚本调用（validate / export）都以这个文件路径为输入。骨架、拓扑、内容填充与定向修复**均直接修改 project.json**，由阶段三 validate.js 校验兜底。
- **下游衔接**：本 skill 完成后，运行 `node /root/zds/zds_app/ifg-runtime/scripts/check_delivery.js <项目目录> --story-only`，error=0 才算剧本交付完成。

## 3. 四阶段推进

按 4 阶段顺序推进，每阶段完成时向用户展示产出并确认后进入下一阶段：

| 阶段 | 参考文件目录 |
|------|-----------|
| 一、故事线框架 | `references/01-story-framework.md` |
| 二、场内拆节点与分支 | `references/02-scene-nodes.md` |
| 三、结构验证 | `references/03-structure-validate.md` |
| 四、叙事化润色 | `references/04-narrative-polish.md` |
