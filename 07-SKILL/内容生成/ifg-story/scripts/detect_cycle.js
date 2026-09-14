// 图环检测器：从 project.json 的 choices 图中找出所有环并报错退出
// 用法: node detect_cycle.js <project.json路径>
const fs = require('fs');
const file = process.argv[2] || 'project.json';
const p = JSON.parse(fs.readFileSync(file, 'utf8'));
const g = {};
(p.nodes || []).forEach(n => { g[n.id] = (n.choices || []).map(c => c.targetNodeId).filter(Boolean); });
const color = {}, stack = [], cycles = [];
function dfs(u) {
  color[u] = 1; stack.push(u);
  for (const v of g[u] || []) {
    if (color[v] === 1) { const i = stack.indexOf(v); cycles.push(stack.slice(i).concat(v)); }
    else if (!color[v]) dfs(v);
  }
  stack.pop(); color[u] = 2;
}
(p.nodes || []).forEach(n => { if (!color[n.id]) dfs(n.id); });
if (cycles.length) {
  console.error(JSON.stringify({
    error: 'GRAPH_CYCLE',
    message: 'choices 图中存在环，validate.js 的可达性检查会死循环；请先修掉以下环（通常是误把带 choices 的节点当结局复制/接线）',
    cycles
  }, null, 2));
  process.exit(2);
}
console.log(JSON.stringify({ ok: true, nodes: (p.nodes || []).length, cycles: 0 }));
