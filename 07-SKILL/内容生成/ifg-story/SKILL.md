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
├── images         # 文件夹
└── 剧本.md
```
- `project.json` 是贯穿全程的**磁盘文件**：每阶段经用户确认的字段立即写入/合并进该文件。
- 后续脚本调用（validate / export）都以这个文件路径为输入。骨架、拓扑、内容填充与定向修复**均直接修改 project.json**。
- **下游衔接**：本 skill 完成后，运行 `node /root/zds/zds_app/ifg-runtime/scripts/check_delivery.js <项目目录> --story-only`，error=0 才算剧本交付完成。

## 3. 写作铁律（全阶段通用）

- **玩家就是主角，不是读者在读小说**：
  - 旁白 `narrative` → **第二人称「你」**写主角；禁止用「他/沈砚」指代主角。
  - 独白 `monologue` → **第一人称「我」**（现在时口语，≤30 字）。
  - 对白 `dialogue` → **不改人称**；引号 `「…」` 内按说话人原话保留。
  - 旁白里的「他/她」只能指**其他角色**，且必须逐句做指代消解（主语是别人→保留；宾语位置/主语不是别人→改「你」）。
- 人称修正**只动人称**：不增删情节、不改动用词，不动 `choices` / `imagePrompt` / `art_prompt`。
- 详见 `references/03-narrative-polish.md`（阶段三）与 `references/data-model.md` 字段注释。

## 4. 五阶段推进

按 5 阶段顺序推进，每阶段完成时向用户展示产出并确认后进入下一阶段：

| 阶段 | 参考文件目录 |
|------|-----------|
| 一、故事线框架 | `references/01-story-framework.md` |
| 二、场内拆节点与分支 | `references/02-scene-nodes.md` |
| 三、叙事化润色 | `references/03-narrative-polish.md` |
| 四、配图生成 | `references/04-illustration.md` |
| 五、部署与启动 | `references/05-deploy.md` |
