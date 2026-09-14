#!/bin/bash
# validate_safe.sh — validate.js 的安全包装：超时熔断 + 图环检测
# 用法: validate_safe.sh <project.json路径> [timeout秒，默认90]
PROJ="${1:-project.json}"
TMO="${2:-90}"
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1) 先做图环检测（毫秒级），有环直接报错，不进 validate
if ! node "$SKILL_DIR/detect_cycle.js" "$PROJ"; then
  exit 2
fi

# 2) 超时熔断：validate 死循环则杀掉，并回读环检测详情
timeout "$TMO" node "$SKILL_DIR/validate.js" "$PROJ"
code=$?
if [ $code -eq 124 ]; then
  echo ""
  echo "═══ VALIDATE 超时熔断 ═══"
  echo "validate.js 运行超过 ${TMO}s 未结束（疑似图死循环），已终止。"
  node "$SKILL_DIR/detect_cycle.js" "$PROJ"
  exit 2
fi
exit $code
