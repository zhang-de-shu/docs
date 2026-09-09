#!/usr/bin/env alink
/**
 * 互动影游项目本地校验脚本
 * 用法：alink scripts/validate.js <项目JSON路径> [--write]
 * 按 26 项检测（结构完整性 16 + 叙事质量 10）输出 ValidationReport 与通过率。
 * 通过率 = 100 − error×20 − warning×8 − info×2（下限 0）。
 * 加 --write 时：报告同时写入项目 JSON 的 lastValidation（校验不通过也会写入，便于修复后对比）。
 */
const fs = require('fs');
const path = require('path');

const file = process.argv[2];
const writeBack = process.argv.includes('--write');
if (!file || !fs.existsSync(file)) {
  console.error('用法: alink scripts/validate.js <项目JSON路径> [--write]');
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
const nodeById = new Map(nodes.map(n => [n.id, n]));
const endings = project.endings || [];
const variables = new Set((project.variables || []).map(v => v.name));
const worldAnchor = project.worldAnchor || {};
const issues = [];

function add(level, code, message, relatedIds) {
  issues.push({ level, code, message, relatedIds: relatedIds || [] });
}

// ---------- 工具 ----------
function choicesOf(n) { return n.choices || []; }

// 条件表达式解析：varName op value，&&/|| 与括号，&& 优先于 ||
function parseCondition(cond) {
  if (!cond || !cond.trim()) return { ok: true, vars: [] };
  const s = cond.trim();
  if (!/^[()!&|=<>A-Za-z0-9_+\-.\s]+$/.test(s)) return { ok: false, vars: [] };
  let i = 0;
  function skip() { while (i < s.length && /\s/.test(s[i])) i++; }
  function parseAtom() {
    skip();
    if (s[i] === '(') {
      i++;
      const v = parseOr();
      skip();
      if (s[i] !== ')') throw '括号不匹配';
      i++;
      return v;
    }
    const m = /^([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)/.exec(s.slice(i));
    if (!m) throw '子式不符合 varName op value: ' + s.slice(i, i + 20);
    i += m[0].length;
    return [{ name: m[1], op: m[2], value: Number(m[3]) }];
  }
  function parseAnd() {
    let v = parseAtom();
    skip();
    while (s.startsWith('&&', i)) { i += 2; v = v.concat(parseAtom()); skip(); }
    return v;
  }
  function parseOr() {
    let v = parseAnd();
    skip();
    while (s.startsWith('||', i)) { i += 2; v = v.concat(parseAnd()); skip(); }
    return v;
  }
  try {
    const vars = parseOr();
    skip();
    if (i < s.length) throw '多余字符';
    return { ok: true, vars };
  } catch (e) {
    return { ok: false, vars: [] , err: String(e)};
  }
}

// variableEffects 解析："name+1,name-1,name=2"
function parseEffects(effects) {
  if (!effects || !effects.trim()) return { ok: true, items: [] };
  const items = [];
  for (const part of effects.split(/[,，]/)) {
    const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\+|-|=)\s*(\d+)\s*$/.exec(part);
    if (!m) return { ok: false, items: [] };
    items.push({ name: m[1], op: m[2], value: Number(m[3]) });
  }
  return { ok: true, items };
}

// ---------- 图构建（含 explore 返回边）----------
function outEdges(n) {
  const edges = [];
  for (const c of choicesOf(n)) {
    if (c.targetNodeId && nodeById.has(c.targetNodeId)) edges.push(c.targetNodeId);
  }
  if (n.type === 'explore' && n.exploreReturnNodeId && nodeById.has(n.exploreReturnNodeId)) {
    edges.push(n.exploreReturnNodeId);
  }
  return edges;
}

const startNode = nodes.find(n => n.type === 'start');
const reachable = new Set();
if (startNode) {
  const q = [startNode.id];
  reachable.add(startNode.id);
  while (q.length) {
    const cur = nodeById.get(q.shift());
    for (const t of outEdges(cur)) {
      if (!reachable.has(t)) { reachable.add(t); q.push(t); }
    }
  }
}

// ---------- 变量理论上界（从 start BFS 沿途累加）----------
const maxVar = {};
(function () {
  if (!startNode) return;
  const best = { [startNode.id]: {} };
  const q = [startNode.id];
  while (q.length) {
    const id = q.shift();
    const acc = best[id];
    const n = nodeById.get(id);
    for (const c of choicesOf(n)) {
      const { items } = parseEffects(c.variableEffects);
      const next = Object.assign({}, acc);
      for (const it of items) {
        if (it.op === '+') next[it.name] = (next[it.name] || 0) + it.value;
        else if (it.op === '=') next[it.name] = Math.max(next[it.name] || 0, it.value);
      }
      const tid = c.targetNodeId;
      if (!tid || !nodeById.has(tid)) continue;
      const old = best[tid];
      const better = !old || Object.keys(next).some(k => next[k] > (old[k] || 0));
      if (better) {
        best[tid] = Object.assign({}, old || {}, next);
        for (const k in next) best[tid][k] = Math.max(best[tid][k], next[k]);
        if (!q.includes(tid)) q.push(tid);
      }
    }
    // explore 返回边不改变变量
    if (n.type === 'explore' && n.exploreReturnNodeId && nodeById.has(n.exploreReturnNodeId)) {
      const tid = n.exploreReturnNodeId;
      if (!best[tid]) { best[tid] = Object.assign({}, acc); q.push(tid); }
    }
  }
  for (const id in best) {
    for (const k in best[id]) maxVar[k] = Math.max(maxVar[k] || 0, best[id][k]);
  }
})();

// ---------- 结构完整性（16 项）----------
// 1. DEAD_END 死路
for (const n of nodes) {
  if (n.type === 'ending') continue;
  const hasReturn = n.type === 'explore' && n.exploreReturnNodeId && nodeById.has(n.exploreReturnNodeId);
  if (outEdges(n).length === 0 && !hasReturn) {
    add('error', 'DEAD_END', `非 ending 节点「${n.title}」无任何有效出口`, [n.id]);
  }
}
// 2. BROKEN_LINK 断链
for (const n of nodes) {
  for (const c of choicesOf(n)) {
    if (c.targetNodeId && !nodeById.has(c.targetNodeId)) {
      add('error', 'BROKEN_LINK', `节点「${n.title}」选项「${c.text}」指向不存在的节点 ${c.targetNodeId}`, [n.id, c.targetNodeId]);
    }
  }
}
// 3. NO_PATH_TO_ENDING 无法到达结局
if (startNode && !nodes.some(n => n.type === 'ending' && reachable.has(n.id))) {
  add('error', 'NO_PATH_TO_ENDING', '从 start 出发没有任何路径能到达 ending 节点');
}
// 4. TRAP_BRANCH 陷阱分支：分支的所有下游路径均无法回到主线或结局
//    实现：从每个 branch 的每个选项终点出发，若都无法到达 ending，且无法汇入从 start 到任一 ending 的主干 → 简化为：无法到达任何 ending
if (startNode) {
  const canReachEnding = new Set();
  for (const n of nodes) {
    if (n.type !== 'ending') continue;
    // 反向可达：从 start 已算过 reachable；终点可达 = reachable 且自身可达 ending（ending 自身可达）
    canReachEnding.add(n.id);
  }
  const reachEnd = new Set(canReachEnding);
  // 反向传播：能到达 reachEnd 中任一节点的节点
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of nodes) {
      if (reachEnd.has(n.id)) continue;
      if (outEdges(n).some(t => reachEnd.has(t))) { reachEnd.add(n.id); changed = true; }
    }
  }
  for (const n of nodes) {
    if (n.type === 'branch' && !reachEnd.has(n.id)) {
      add('error', 'TRAP_BRANCH', `分支节点「${n.title}」的所有下游路径均无法回到主线或结局`, [n.id]);
    }
  }
}
// 5. ENDING_ORPHAN 孤儿结局定义
const endingNodeIds = new Set(nodes.filter(n => n.type === 'ending').map(n => n.id));
for (const e of endings) {
  if (e.nodeId && !endingNodeIds.has(e.nodeId)) {
    add('error', 'ENDING_ORPHAN', `结局定义「${e.title || e.nodeId}」没有对应的 ending 节点`, [e.nodeId]);
  }
}
// 6. UNSATISFIABLE_CONDITION 条件永不可满足（含结局触发条件）
for (const n of nodes) {
  for (const c of choicesOf(n)) {
    const p = parseCondition(c.conditions);
    if (!p.ok) { add('warning', 'UNPARSEABLE_EFFECT', `节点「${n.title}」选项条件语法错误: ${c.conditions}`, [n.id]); continue; }
    for (const v of p.vars) {
      const bound = maxVar[v.name];
      if (bound === undefined) continue; // 未定义变量由 UNKNOWN_VARIABLE_REF 报
      let unsat = false;
      if (v.op === '>=' && v.value > bound) unsat = true;
      if (v.op === '>' && v.value >= bound) unsat = true;
      if (v.op === '==' && v.value > bound) unsat = true;
      if (unsat) add('error', 'UNSATISFIABLE_CONDITION', `节点「${n.title}」选项「${c.text}」条件 ${c.conditions} 超过变量 ${v.name} 的理论最大累计值 ${bound}，永不可满足`, [n.id]);
    }
  }
}
for (const e of endings) {
  const cond = e.conditions || e.variableConditions || '';
  const p = parseCondition(cond);
  if (cond && !p.ok) add('warning', 'UNPARSEABLE_EFFECT', `结局「${e.title}」触发条件语法错误: ${cond}`, [e.nodeId]);
  if (p.ok) for (const v of p.vars) {
    const bound = maxVar[v.name];
    if (bound === undefined) continue;
    let unsat = (v.op === '>=' && v.value > bound) || (v.op === '>' && v.value >= bound) || (v.op === '==' && v.value > bound);
    if (unsat) add('error', 'UNSATISFIABLE_CONDITION', `结局「${e.title}」条件 ${cond} 超过变量 ${v.name} 理论上界 ${bound}，永不可达`, [e.nodeId]);
  }
}
// 7. UNREACHABLE 不可达节点
for (const n of nodes) {
  if (!reachable.has(n.id)) add('warning', 'UNREACHABLE', `节点「${n.title}」从 start 不可达`, [n.id]);
}
// 8. NO_ENDING 无结局
if (!nodes.some(n => n.type === 'ending')) add('warning', 'NO_ENDING', '项目没有任何 ending 节点');
// 9. DUPLICATE_CHOICE 重复选项文本（跨节点）
const choiceTextOwners = new Map();
for (const n of nodes) {
  for (const c of choicesOf(n)) {
    if (!c.text) continue;
    if (!choiceTextOwners.has(c.text)) choiceTextOwners.set(c.text, []);
    choiceTextOwners.get(c.text).push(n.id);
  }
}
for (const [text, owners] of choiceTextOwners) {
  if (owners.length > 1) add('warning', 'DUPLICATE_CHOICE', `不同节点出现完全相同的选项文字「${text}」`, owners);
}
// 10. ENDING_NO_DEF 结局节点缺定义
const definedEndingNodes = new Set(endings.map(e => e.nodeId).filter(Boolean));
for (const n of nodes) {
  if (n.type === 'ending' && !definedEndingNodes.has(n.id)) {
    add('warning', 'ENDING_NO_DEF', `ending 节点「${n.title}」未在结局定义中登记（中途即死 BE 应自动生成 bad 类型定义）`, [n.id]);
  }
}
// 11/12. UNKNOWN_VARIABLE_REF / UNPARSEABLE_EFFECT
for (const n of nodes) {
  for (const c of choicesOf(n)) {
    const p = parseCondition(c.conditions);
    if (c.conditions && c.conditions.trim()) {
      if (!p.ok) add('warning', 'UNPARSEABLE_EFFECT', `节点「${n.title}」选项条件无法解析: ${c.conditions}（运行时不会执行）`, [n.id]);
      else for (const v of p.vars) {
        if (!variables.has(v.name)) add('warning', 'UNKNOWN_VARIABLE_REF', `节点「${n.title}」条件引用未定义变量 ${v.name}`, [n.id]);
      }
    }
    if (c.variableEffects && c.variableEffects.trim()) {
      const eff = parseEffects(c.variableEffects);
      if (!eff.ok) add('warning', 'UNPARSEABLE_EFFECT', `节点「${n.title}」选项「${c.text}」variableEffects 无法解析: ${c.variableEffects}`, [n.id]);
      else for (const it of eff.items) {
        if (!variables.has(it.name)) add('warning', 'UNKNOWN_VARIABLE_REF', `节点「${n.title}」variableEffects 引用未定义变量 ${it.name}`, [n.id]);
      }
    }
  }
}
// 13. ALL_CHOICES_GATED 无保底出口
for (const n of nodes) {
  const cs = choicesOf(n);
  if (cs.length > 0 && cs.every(c => c.conditions && String(c.conditions).trim())) {
    add('warning', 'ALL_CHOICES_GATED', `节点「${n.title}」全部选项都带条件，玩家可能被软锁卡死`, [n.id]);
  }
}
// 14. 终章单点扇出：多个结局节点的直接前置是同一个选择节点（domain-baseline §3）
{
  // 每个结局节点：找其直接前置（某节点的选项/出口直接指向它）
  const endingPredecessors = new Map(); // endingNodeId -> Set(prevNodeId)
  for (const n of nodes) {
    for (const t of outEdges(n)) {
      if (nodeById.get(t)?.type === 'ending') {
        if (!endingPredecessors.has(t)) endingPredecessors.set(t, new Set());
        endingPredecessors.get(t).add(n.id);
      }
    }
  }
  // 判定：某非 ending 节点是 ≥2 个结局的直接前置，且这些结局均无"只属于该路线的专属小节"
  const endingCountByPrev = new Map();
  for (const [endId, prevs] of endingPredecessors) {
    for (const pv of prevs) {
      if (!endingCountByPrev.has(pv)) endingCountByPrev.set(pv, []);
      endingCountByPrev.get(pv).push(endId);
    }
  }
  for (const [prevId, endIds] of endingCountByPrev) {
    if (endIds.length < 2) continue;
    const prev = nodeById.get(prevId);
    // 违规判定：该前置节点的选项直接指向 ≥2 个 ending（没有专属场景夹层）
    const directEndingTargets = outEdges(prev).filter(t => nodeById.get(t)?.type === 'ending');
    if (directEndingTargets.length >= 2 && prev.type !== 'ending') {
      add('error', 'ENDING_SINGLE_FANOUT', `节点「${prev.title}」的选项直接通向 ${directEndingTargets.length} 个结局（${directEndingTargets.map(t => nodeById.get(t).title).join('、')}）——终章单点扇出，玩家的全程积累未参与裁决；每个结局前必须有专属前置小节`, [prevId, ...directEndingTargets]);
    }
  }
}
// 15. BE 密度：每章即死 BE 岔口 4-8 个（第 1 章必须 ≥1 个完成选择教学）
{
  const chapOf = (id) => { const m = /^c(\d+)/.exec(String(id)); return m ? Number(m[1]) : null; };
  const beByChapter = new Map();
  for (const n of nodes) {
    if (n.type !== 'branch') continue;
    const isBE = /即死岔口|改为即死结局/.test((n.title || '') + (n.notes || ''));
    if (!isBE) continue;
    const c = chapOf(n.id);
    if (c === null) continue;
    beByChapter.set(c, (beByChapter.get(c) || 0) + 1);
  }
  if (beByChapter.size > 0) {
    for (const [c, cnt] of beByChapter) {
      if (cnt < 4) add('warning', 'BE_DENSITY_LOW', `第${c}章即死 BE 岔口仅 ${cnt} 个（基准 4-8 个，占选择节点 20-30%）——互动密度不足，会退化成"可点击的短剧"`);
      if (cnt > 8) add('info', 'BE_DENSITY_HIGH', `第${c}章即死 BE 岔口 ${cnt} 个，超过基准上限 8 个，检查是否惩罚过密`);
    }
    // 第 1 章：必须有 BE（选择即后果教学）
    const firstChapterWithNodes = Math.min(...nodes.map(n => chapOf(n.id)).filter(v => v !== null));
    if (firstChapterWithNodes === 1 && !(beByChapter.get(1) >= 1)) {
      add('warning', 'NO_FIRST_CHAPTER_BE', '第 1 章没有任何即死 BE 岔口——缺失"选择即后果"教学，玩家不会把后续选择当真');
    }
  }
}
// 16. normal 推进节点须有 2-3 个真选择（domain-baseline §2.1 选择密度）
for (const n of nodes) {
  if (n.type !== 'normal' && n.type !== 'start' && n.type !== 'merge') continue;
  const cs = choicesOf(n);
  if (n.type === 'normal' && cs.length === 1) {
    add('warning', 'SINGLE_FAKE_CHOICE', `normal 节点「${n.title}」仅 1 个选项（"继续"式单选项=伪互动），须 2-3 个真选择（同目标不同语气/变量效果）`, [n.id]);
  }
}

// ---------- 叙事质量（10 项）----------
for (const n of nodes) {
  const lines = (n.dialogue || []).length;
  if (n.type !== 'explore' && lines > 0 && lines < 6) {
    add('warning', 'THIN_DIALOGUE', `节点「${n.title}」对白仅 ${lines} 行（McKee 标准 ≥6）`, [n.id]);
  }
}
const totalDuration = nodes.reduce((s, n) => s + (n.durationSeconds || 0), 0);
const target = (worldAnchor.durationMinutes || 0) * 60;
if (target > 0 && totalDuration < target * 0.5) {
  add('warning', 'SHORT_DURATION', `全部节点预估时长合计 ${Math.round(totalDuration / 60)} 分钟 < 目标时长 ${worldAnchor.durationMinutes} 分钟的 50%`);
}
const filledEmotion = nodes.filter(n => n.emotionFunction && typeof n.emotionFunction.tension === 'number');
if (filledEmotion.length >= 5) {
  const highT = filledEmotion.filter(n => n.emotionFunction.tension >= 7).length;
  if (highT / filledEmotion.length > 0.7) {
    add('info', 'EMOTION_MONOTONE', `已填情感节点中 tension≥7 占比 ${Math.round(highT / filledEmotion.length * 100)}% > 70%，建议加 1-2 个呼吸节点（tension≤3）`);
  }
}
const endingNodes = nodes.filter(n => n.type === 'ending');
if (endingNodes.length === 1) add('info', 'SINGLE_ENDING', '全片仅 1 个结局');
const endingTypes = new Set(endings.map(e => e.type));
if (endingNodes.length > 1 && (endingTypes.size <= 1)) add('info', 'ENDING_VARIETY', '各结局的情感基调/类型过于相近');
const branchCount = nodes.filter(n => n.type === 'branch').length;
if (nodes.length > 0 && branchCount / nodes.length < 0.25) {
  add('info', 'LOW_BRANCH_DENSITY', `branch 节点占比 ${Math.round(branchCount / nodes.length * 100)}% < 25%`);
}
// WEAK_CHOICES：假分支（所有选项指向同一目标且无 variableEffects 差异）
for (const n of nodes) {
  const cs = choicesOf(n);
  if (cs.length >= 2) {
    const sameTarget = cs.every(c => c.targetNodeId === cs[0].targetNodeId);
    const effects = new Set(cs.map(c => c.variableEffects || ''));
    if (sameTarget && effects.size <= 1) {
      add('info', 'WEAK_CHOICES', `节点「${n.title}」所有选项指向同一目标且无 variableEffects 差异（假分支）`, [n.id]);
    }
  }
}
if (!nodes.some(n => n.type === 'explore')) add('info', 'NO_EXPLORE_CONTENT', '全片没有 explore 节点');
for (const n of nodes) {
  if (n.emotionFunction && !n.emotionFunction.internal_lie) {
    add('info', 'SHALLOW_EMOTION', `节点「${n.title}」情感弧未填 internal_lie`, [n.id]);
  }
}
for (const n of nodes) {
  if (!n.sceneDesc || n.sceneDesc.trim().length < 10) {
    add('info', 'THIN_SCENE_DESC', `节点「${n.title}」sceneDesc 过短或为空`, [n.id]);
  }
}

// ---------- 汇总 ----------
const count = { error: 0, warning: 0, info: 0 };
for (const it of issues) count[it.level]++;
const passRate = Math.max(0, 100 - count.error * 20 - count.warning * 8 - count.info * 2);

const report = {
  generatedAt: new Date().toISOString(),
  totalNodes: nodes.length,
  totalBranches: branchCount,
  issues,
  passRate,
};

console.log(JSON.stringify(report, null, 2));
if (writeBack) {
  project.lastValidation = report;
  fs.writeFileSync(file, JSON.stringify(project, null, 2) + '\n');
  console.error(`校验报告已写入 ${file}（lastValidation）。`);
}
console.error(`\n通过率: ${passRate}（error ${count.error} / warning ${count.warning} / info ${count.info}）`);
process.exit(count.error > 0 ? 1 : 0);
