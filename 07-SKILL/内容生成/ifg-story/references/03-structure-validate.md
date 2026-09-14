# 阶段三：结构验证（structure validate）

本阶段做两件事：**跑脚本，把结构修到闭环**；**输出互动密度与结构摘要，经用户确认**。不检查任何写作质量。

## 唯一门槛

```bash
node scripts/validate.js <项目JSON路径> --write
```

**error 必须为 0**，且覆盖三类闭环问题：
- `DEAD_END`：分支无死路（非 ending 节点必须有有效出口）
- `TRAP_BRANCH`：无困在分支里回不到主线或结局的路径
- 结局全部可达（从 start 出发每条结局线都走得到）

## BE 密度与结构检测（供用户确认）

validate.js 会对 AI 生成的骨架做量化结构检测（不达标报 warning/info，不阻断交付也不修改但须向用户如实展示）：
- 每章节点数 20-30（序章 10-15）；branch 占比 ≥25%
- 即死 BE：序章 1-2 个、正章每章 4-8 个；`BE_CLUSTERED` 检测 BE 是否集中堆放而非间隔散布；`FIRST_BE_LATE` 检测第 1 章首个 BE 是否在前 5 节点内

## 工作步骤

1. 执行 validate.js --write，报告写入 project.json 的 `lastValidation`（校验不通过也会写入，便于修复后对比）。error > 0 时进程以非零码退出。
2. **把脚本 stderr 末尾的「互动密度与结构摘要」原样展示给用户**（每章节点数/BE 数/分支占比、✓/✗ 对照基准），并确认是否接受；BE 密度或节点数不达标时，先定向补齐结构再继续。
3. 有 error 时做**定向修复**（structure:targeted_fix）：只做节点级补丁——加节点 / 改节点 / 加选项 / 改选项 / 设 explore 返回 / 登记结局六类；每次修复须能对应到具体 issue；新增/修改选项若带 conditions，该节点必须保留无条件选项；单轮 ≤25 处，其余留下一轮。修复按 SKILL.md「写入口规则」以精确 patch 方式直接修改 project.json。
4. 修复后**重跑校验**，展示通过率前后对比；循环至 error 清零且密度摘要经用户确认。

## 产物

`lastValidation` 写入 project.json（error 0、分支闭环、密度摘要经用户确认）。确认后进入阶段四。
