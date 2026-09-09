# 阶段三：结构验证（structure validate）

本阶段只做一件事：**跑脚本，把结构修到闭环**。不检查任何写作质量。

## 唯一门槛

```bash
node scripts/validate.js <项目JSON路径> --write
```

**error 必须为 0**，且覆盖三类闭环问题：
- `DEAD_END`：分支无死路（非 ending 节点必须有有效出口）
- `TRAP_BRANCH`：无困在分支里回不到主线或结局的路径
- 结局全部可达（从 start 出发每条结局线都走得到）

warning / info 不作为交付门槛（写作建议仅供参考）。

## 工作步骤

1. 执行 validate.js --write，报告写入 project.json 的 `lastValidation`（校验不通过也会写入，便于修复后对比）。error > 0 时进程以非零码退出。
2. 有 error 时生成**定向修复 ops**（structure:targeted_fix）：只做节点级补丁——add_node / update_node / add_choice / update_choice / set_explore_return / bind_ending 六种；每个 op 的 reason 必须指明对应哪条 issue；新增/修改选项若带 conditions，该节点必须保留无条件选项；ops ≤25 条，其余留下一轮。ops 经 fill-nodes.js 应用：
   ```bash
   node scripts/fill-nodes.js <项目JSON路径> <opsJSON路径>
   ```
3. 修复后**重跑校验**，展示通过率前后对比；循环至 error 清零。

## 产物

`lastValidation` 写入 project.json（error 0、分支闭环）。确认后进入阶段四。
