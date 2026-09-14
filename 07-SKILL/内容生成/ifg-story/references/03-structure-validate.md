# 阶段三：结构验证（structure validate）


## 执行脚本

```bash
node scripts/validate.js <项目JSON路径> --write
```

**error 必须为 0**，且覆盖三类闭环问题：
- `DEAD_END`：分支无死路（非 ending 节点必须有有效出口）
- `TRAP_BRANCH`：无困在分支里回不到主线或结局的路径
- 结局全部可达（从 start 出发每条结局线都走得到）

## 工作步骤

1. 执行 validate.js --write，报告写入 project.json 的 `lastValidation`（校验不通过也会写入，便于修复后对比）。error > 0 时进程以非零码退出。
2. **把脚本 stderr 末尾的「互动密度与结构摘要」原样展示给用户**（每章节点数/BE 数/分支占比、✓/✗ 对照基准），并确认是否接受；BE 密度或节点数不达标时，先定向补齐结构再继续。密度基准值以脚本输出的摘要为唯一对照标准（定量基准已内置于 validate.js，文档不另设数字，避免双重事实源）。
3. 有 error 时做**定向修复**（structure:targeted_fix）：只做节点级补丁——加节点 / 改节点 / 加选项 / 改选项 / 设 explore 返回 / 登记结局六类；每次修复须能对应到具体 issue；新增/修改选项若带 conditions，该节点必须保留无条件选项；单轮 ≤25 处，其余留下一轮。修复按 SKILL.md「写入口规则」以精确 patch 方式直接修改 project.json。
4. 修复后**重跑校验**，展示通过率前后对比；循环至 error 清零且密度摘要经用户确认。

- `scripts/` 下所有脚本一律当作黑盒：只允许执行，禁止 read 或解释其源码，禁止在思考中推演、复算或预演其输出。脚本实现与你的工作无关。
- 脚本 stdout 中的 JSON 是唯一事实：校验报告、nodeId、targetNodeId 一律原样采信与复制，不验证、不"修正"、不凭记忆重写。
- 脚本报错时只有三个动作：把 stderr 原样展示给用户 → 原样重试 1 次 → 仍失败则停下询问用户。不存在第四个动作（尤其不是读源码排查）。


## 产物

`lastValidation` 写入 project.json（error 0、分支闭环、密度摘要经用户确认）。确认后进入阶段四。
