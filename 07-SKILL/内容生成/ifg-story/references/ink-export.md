# ink 导出规范（源自原项目 lib/persistence.ts exportInk）

最终交付必须输出 Inkle ink 脚本（story.ink），规则如下：

## 变量声明

- 每个 `project.variables` 的变量用 `VAR name = 初值` 声明；数值直接写，字符串加引号（`VAR flag = "off"`）。
- **变量名净化**：非 `[a-zA-Z0-9_]` 字符替换为 `_`；以数字开头加前缀 `var_`；全非法字符时用字符码和哈希（`var_<hash>`）。改名后写注释 `// 变量映射: converted = "原名"`。
- **自洽铁律**：正文（variableEffects / conditions）实际引用到但未登记的变量，必须补齐 `VAR` 声明（初值 0，set 字符串则用字符串），否则 .ink 编译不过——不能依赖作者是否做过变量登记。

## 选项与条件

- 选项行：`+ [选项文字] -> target_knot`；带条件时用 ink 条件语法 `{ varName >= 4: -> target | -> other }`。
- 条件转换与求值器同构：保留括号与 `&& / ||` 的原有结构（递归下降），变量名同样净化；无法解析的子式丢弃该条件（退化为无条件选项）。

## 变量效果

- variableEffects 按逗号拆分，逐项解析（同时认识 `name+1` / `+name` / `name=value` 写法），产出 ink 行：
  - set：`~ name = 值`（字符串加引号）
  - inc/dec：`~ name = name + N` / `~ name = name - N`

## 节点与结构

- 每个 StoryNode 一个 knot（`=== knot_name ===`）；场景描述与对白作为 knot 内文本；选项用 stitch/分流组织。
- explore 节点：进入支线后由 `exploreReturnNodeId` 返回主线，导出为"进入即返回"的跳转。
- ending 节点：`->->` 收束或 `END`。

## 文件头

```
// {项目标题}
// 互动影游导出 · {日期}
```

## 同步导出 JSON

完整 Project JSON（`references/data-model.md` 结构）随 .ink 一并交付，JSON 为事实来源，ink 为播放格式。
