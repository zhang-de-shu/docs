#!/usr/bin/env alink
/**
 * 分支拓扑推导脚本（移植自原项目 lib/ai/prompts/branches.ts「branches:generate」第一步）
 *
 * 用法：alink scripts/build-topology.js <项目JSON路径>
 * 输入：项目 JSON（须已含 nodes——骨架填充后的全部章节节点；worldAnchor.endingsDesign 用于门控提示）
 * 输出：连接拓扑 JSON + 人类可读拓扑行（stdout），AI 据此逐节点写选项文字；
 *       targetNodeId 必须完全按拓扑填写，禁止更改。
 *
 * 拓扑规则：
 * - 从每个 branch 向后扫描至 merge（汇回）或下一个 branch/start（不汇合——终章路线门控）
 * - 优先按节点 notes 的 [路径X] 标签分组还原路径归属；标签缺失时退回按 ending 切块
 * - branch+merge → 菱形/平行路线；branch 无 merge+多路线块 → 终章路线门控；
 *   branch 无路线块 → 变量积累型；explore → exploreReturnNodeId；normal/merge → 下一非 explore 非 ending 节点
 */
const fs = require('fs');

const file = process.argv[2];
if (!file || !fs.existsSync(file)) {
  console.error('用法: alink scripts/build-topology.js <项目JSON路径>');
  process.exit(2);
}

let project;
try {
  project = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
  console.error('JSON 解析失败: ' + e.message);
  process.exit(2);
}

const nodes = project.nodes || [];
const world = project.worldAnchor || {};
const endingsDesign = world.endingsDesign || [];
const endingInfoByTitle = new Map(endingsDesign.map(e => [e.title, e]));

// ── 第一步：预计算每个 branch 的路线块与类型 ──────────────────────
const PATH_TAG_RE = /^\[路径([A-Za-z0-9]+)\]/;
const pathTagOf = (node) => PATH_TAG_RE.exec(node.notes ?? '')?.[1] ?? null;

const branchScans = new Map();
const routeNodeNext = new Map();

for (let i = 0; i < nodes.length; i++) {
  if (nodes[i].type !== 'branch') continue;

  const region = [];
  let mergeNode = null;
  for (let j = i + 1; j < nodes.length; j++) {
    const x = nodes[j];
    if (x.type === 'explore') continue;
    if (x.type === 'merge') { mergeNode = x; break; }
    if (x.type === 'branch' || x.type === 'start') break;
    if (x.type === 'normal' || x.type === 'ending') { region.push(x); continue; }
    break;
  }
  if (region.length === 0 && !mergeNode) continue;

  const tags = region.map(pathTagOf);
  const tagged = region.length > 0 && tags.every(t => t !== null);

  let blocks;
  if (tagged) {
    const order = [];
    const groups = new Map();
    region.forEach((x, idx) => {
      const t = tags[idx];
      if (!groups.has(t)) { groups.set(t, []); order.push(t); }
      groups.get(t).push(x);
    });
    blocks = order.map(t => {
      const groupNodes = groups.get(t);
      if (groupNodes.length === 1 && groupNodes[0].type === 'ending') {
        return { normals: [], ending: groupNodes[0] };
      }
      return { normals: groupNodes.filter(x => x.type === 'normal'), ending: null };
    });
  } else {
    blocks = [];
    let curNormals = [];
    for (const x of region) {
      if (x.type === 'ending') {
        blocks.push({ normals: curNormals, ending: x });
        curNormals = [];
      } else {
        curNormals.push(x);
      }
    }
    if (curNormals.length > 0) blocks.push({ normals: curNormals, ending: null });
  }

  if (blocks.length === 0) continue;
  branchScans.set(nodes[i].id, { blocks, mergeNode, tagged });

  for (const block of blocks) {
    for (let k = 0; k < block.normals.length; k++) {
      const isLastInBlock = k === block.normals.length - 1;
      const target = !isLastInBlock ? block.normals[k + 1] : (block.ending ?? mergeNode ?? null);
      if (target) routeNodeNext.set(block.normals[k].id, target);
    }
  }
}

const endingHint = (endingTitle) => {
  const info = endingInfoByTitle.get(endingTitle);
  if (!info) return ' （需在conditions写对应变量条件，0-10整数量表，阈值3-6）';
  return info.keyVariable
    ? ` （对应结局「${info.title}」，conditions必须使用其关键变量：${info.keyVariable}，禁止另选变量或改用百分比）`
    : ` （对应结局「${info.title}」，triggerCondition=${info.triggerCondition ?? ''}；conditions填0-10整数量表下的变量阈值，阈值3-6）`;
};

// ── 第二步：构建连接拓扑 ──────────────────────────────────────────
const conns = [];
for (let i = 0; i < nodes.length; i++) {
  const n = nodes[i];
  if (n.type === 'ending') continue;

  if (n.type === 'explore') {
    const ret = nodes.slice(i + 1).find(x => x.type !== 'explore' && x.type !== 'ending');
    if (ret) conns.push({ from: n, targets: [ret], role: 'advance' });
    continue;
  }

  if (n.type === 'branch') {
    const scan = branchScans.get(n.id);
    if (!scan || scan.blocks.length === 0) {
      const next = nodes.slice(i + 1).find(x => x.type !== 'explore' && x.type !== 'ending');
      if (next) conns.push({ from: n, targets: [next], role: 'branch', branchKind: 'variable' });
    } else if (scan.mergeNode) {
      const targets = (scan.tagged
        ? scan.blocks.map(b => b.normals[0] ?? b.ending)
        : (scan.blocks.length === 1 ? scan.blocks[0].normals : scan.blocks.map(b => b.normals[0] ?? b.ending))
      ).filter(Boolean);
      if (targets.length > 0) conns.push({ from: n, targets, role: 'branch', branchKind: 'diamond' });
    } else if (scan.blocks.length >= 2) {
      const routeEntries = scan.blocks.map(b => b.normals[0] ?? b.ending).filter(Boolean);
      const routeEndings = scan.blocks.map(b => b.ending);
      conns.push({ from: n, targets: routeEntries, role: 'branch', branchKind: 'route', endings: routeEndings });
    } else if (scan.blocks.length === 1 && scan.blocks[0].ending && scan.blocks[0].normals.length === 0) {
      const endings = scan.blocks.map(b => b.ending).filter(Boolean);
      conns.push({ from: n, targets: endings, role: 'branch', branchKind: 'terminal', endings });
    } else {
      const next = scan.blocks[0].normals[0] ?? scan.blocks[0].ending;
      if (next) conns.push({ from: n, targets: [next], role: 'branch', branchKind: 'variable' });
    }
    continue;
  }

  if (routeNodeNext.has(n.id)) {
    conns.push({ from: n, targets: [routeNodeNext.get(n.id)], role: 'advance' });
    continue;
  }

  const next = nodes.slice(i + 1).find(x => x.type !== 'explore' && x.type !== 'ending');
  if (next) conns.push({ from: n, targets: [next], role: 'advance' });
  const nearExplore = nodes[i + 1]?.type === 'explore' ? nodes[i + 1] : null;
  if (nearExplore) conns.push({ from: n, targets: [nearExplore], role: 'explore_trigger' });
}

// ── 人类可读拓扑行（供 AI 提示词直接嵌入）────────────────────────
const routeNodeIds = new Set(routeNodeNext.keys());
const topoLines = conns.map(conn => {
  const fromStr = `"${conn.from.title}"[id:${conn.from.id}]`;
  if (conn.role === 'branch') {
    const kind = conn.branchKind ?? 'variable';
    const kindLabel = kind === 'route' ? '路线门控（每个选项进入专属路线，永不汇合）'
      : kind === 'terminal' ? '终章直通结局（永久分叉）'
      : kind === 'diamond' ? '菱形分支（每个选项有独立专属场景，之后汇回续接节点；若某选项目标标了[结局/即死BE]，选中即立刻触发该BE）'
      : '变量积累（所有选项指向同一节点，仅variableEffects不同）';
    const targetsStr = conn.targets.map((t, idx) => {
      if (kind === 'diamond' && t.type === 'ending') {
        return `    选项${idx + 1}: "${t.title}"[id:${t.id}] [结局/即死BE]（文案必须有吸引力或危险诱惑、不能一眼看出是死路；选中后立刻触发该结局，不写variableEffects/conditions）`;
      }
      const relatedEnding = kind === 'route' ? (conn.endings?.[idx] ?? null) : (kind === 'terminal' ? t : null);
      const hint = (kind === 'route' || kind === 'terminal') && relatedEnding ? endingHint(relatedEnding.title) : '';
      return `    选项${idx + 1}: "${t.title}"[id:${t.id}]${t.type === 'ending' ? ' [结局]' : ''}${hint}`;
    }).join('\n');
    return `${fromStr}[branch/${kind}] → ${kindLabel}:\n${targetsStr}`;
  }
  if (conn.from.type === 'explore') {
    return `${fromStr}[explore] → exploreReturnNodeId必须设为: "${conn.targets[0].title}"[id:${conn.targets[0].id}]，choices=[]`;
  }
  if (conn.role === 'explore_trigger') {
    return `${fromStr} → 【可选】可加一个轻量选项指向explore: "${conn.targets[0].title}"[id:${conn.targets[0].id}]`;
  }
  const tag = routeNodeIds.has(conn.from.id) ? '[路线节点]' : '';
  if (conn.from.type === 'normal') {
    return `${fromStr}${tag} → 【必须，2-3个选项】所有选项均指向同一节点: "${conn.targets[0].title}"[id:${conn.targets[0].id}]（选项间variableEffects/语气不同，至少一个选项带具体variableEffects）`;
  }
  return `${fromStr}${tag} → 【必须】推进选项指向: "${conn.targets[0].title}"[id:${conn.targets[0].id}]`;
}).join('\n');

const needChoices = nodes.filter(n => n.type !== 'ending');

const result = {
  topology: conns.map(c => ({
    fromId: c.from.id,
    fromTitle: c.from.title,
    fromType: c.from.type,
    role: c.role,
    branchKind: c.branchKind ?? null,
    targets: c.targets.map(t => ({ id: t.id, title: t.title, type: t.type })),
  })),
  needChoiceNodes: needChoices.map(n => ({ id: n.id, title: n.title, type: n.type })),
  topoText: topoLines,
};

console.log(JSON.stringify(result, null, 2));
console.error(`\n拓扑就绪：${conns.length} 条连接，${needChoices.length} 个节点待写选项。topoText 可直接嵌入选项设计提示词。`);
