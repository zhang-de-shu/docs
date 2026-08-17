---
name: cli-anything
description: "为任意开源软件自动生成 Agent 可用的 CLI 接口。当用户要求为某个软件生成 CLI、创建命令行工具包装器、让软件变成 Agent 可调用的工具时使用此 skill。支持生成(cli-anything)、增量优化(refine)、测试(test)、验证(validate)四个命令。"
---

# CLI-Anything: Making ALL Software Agent-Native

为任意开源软件自动生成生产级 CLI 接口，让 AI Agent 能通过结构化命令操控专业软件（GIMP、Blender、Inkscape 等），而非脆弱的 GUI 自动化。

## CRITICAL: 执行前必读

**在执行任何操作前，你必须先 Read `references/HARNESS.md`。** 它定义了完整的七阶段流水线方法论、架构标准和实现模式。所有操作都必须遵循 HARNESS.md，不要自由发挥。

## 可用命令

### 1. cli-anything — 生成完整 CLI

为目标软件源码生成完整的 CLI harness。

```
用法: cli-anything <software-path-or-repo>

示例:
  cli-anything /path/to/gimp
  cli-anything https://github.com/blender/blender
```

**执行流程**（详见 `references/commands/cli-anything.md`）：

1. Phase 0: 源码获取（如果是 GitHub URL 则 clone）
2. Phase 1: 源码分析 — 扫描代码，映射 GUI 操作到 API
3. Phase 2: 架构设计 — 设计命令分组、状态模型、输出格式
4. Phase 3: 实现 — 构建 Click CLI，含 REPL、`--json`、undo/redo
5. Phase 4: 测试规划 — 生成 TEST.md
6. Phase 5: 测试编写 — 单元测试 + 端到端测试
7. Phase 6: 文档生成 — 更新 TEST.md、生成 SKILL.md
8. Phase 7: 发布安装 — 创建 setup.py，`pip install -e .`

**成功标准**: 所有测试 100% 通过，CLI 可通过 `which cli-anything-<software>` 发现。

### 2. refine — 增量优化覆盖率

对已有 CLI 进行增量扩展，补充未覆盖的功能。

```
用法: refine <software-path> [focus]

示例:
  refine /path/to/gimp
  refine /path/to/blender "particle systems and physics simulation"
```

**执行流程**（详见 `references/commands/refine.md`）：

1. 盘点当前覆盖范围
2. 分析软件完整能力集
3. 差距分析（优先高影响、易实现、可组合的功能）
4. 实现新命令
5. 扩展测试
6. 更新文档

### 3. test — 运行测试

```
用法: test <software-path-or-repo>
```

运行 pytest，更新 TEST.md。详见 `references/commands/test.md`。

### 4. validate — 验证标准

```
用法: validate <software-path-or-repo>
```

检查 CLI 是否符合 HARNESS.md 的 52 项标准（目录结构、实现标准、测试标准、文档标准、PyPI 打包等）。详见 `references/commands/validate.md`。

## 核心设计原则

1. **真实后端集成** — 必须调用真实软件后端（Blender bpy、GIMP Script-Fu 等），禁止用 Pillow 替代 GIMP 等重新实现
2. **后端缺失 = 测试 fail** — 软件没装时测试必须失败（fail），不允许跳过（skip）
3. **不信任退出码** — 必须独立验证输出内容，防止"看起来通过但什么都没验的"测试
4. **双模式交互** — 子命令模式（脚本/Agent 调用）+ REPL 模式（交互式会话）
5. **`--json` 全覆盖** — 所有命令支持 `--json` 输出结构化数据

## 产物结构

```
<software>/agent-harness/
├── <SOFTWARE>.md              # 软件能力分析 SOP
├── setup.py                   # PyPI 打包（namespace packages）
└── cli_anything/<software>/
    ├── <software>_cli.py      # Click CLI 主入口
    ├── core/                  # 项目管理、会话、导出等
    ├── utils/
    │   ├── repl_skin.py       # REPL 统一皮肤（从 scripts/repl_skin.py 复制）
    │   └── <software>_backend.py
    ├── tests/
    │   ├── TEST.md
    │   ├── test_core.py
    │   └── test_full_e2e.py
    └── skills/SKILL.md
```

## 可用资源

实现过程中可按需 Read 以下文件：

| 文件 | 何时读取 |
|------|---------|
| `references/HARNESS.md` | **必读** — 开始任何操作前 |
| `references/commands/*.md` | 执行对应命令时 |
| `references/guides/auto-save-dry-run.md` | 实现会话型 CLI 时 |
| `references/guides/session-locking.md` | 处理并发会话时 |
| `references/guides/preview-methodology.md` | 实现预览功能时 |
| `references/guides/pypi-publishing.md` | Phase 7 发布时 |
| `references/guides/skill-generation.md` | Phase 6.5 生成 SKILL.md 时 |
| `scripts/repl_skin.py` | Phase 3 实现 REPL 时，复制到产物的 `utils/` |
| `scripts/skill_generator.py` | Phase 6.5 生成 SKILL.md 时 |
| `templates/SKILL.md.template` | Phase 6.5 渲染 SKILL.md 时 |

## 环境要求

- Python 3.10+
- `pip install click pytest`
- 目标软件需本地安装（CLI 直连后端引擎）
