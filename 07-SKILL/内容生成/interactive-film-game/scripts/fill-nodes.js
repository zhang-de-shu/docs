#!/usr/bin/env alink
/**
 * 节点内容填充脚本——AI 与 project.json 之间唯一的内容写入口。
 * 计数、id 分配、结构落盘一律不让模型做：本脚本只接受声明式 JSON，预校验全过后一次性写入。
 *
 * 用法：alink scripts/fill-nodes.js <项目JSON路径> <填充JSON路径>
 *       （填充JSON路径为 - 时从 stdin 读）
 *
 * 填充 JSON（顶层字段全部可选，按需提供；任一校验失败则整批拒绝写入，exit 1）：
 * {
 *   "chapters": { "<章order>": {"title": "..."} },
 *   "titles":   { "<nodeId>": {"title": "...", "notes": "..."} },
 *   "nodeContent": { "<nodeId>": { "sceneHeader": {"location","timeOfDay","interior"},
 *                                  "sceneDesc": "...", "emotionFunction": {...},
 *                                  "dialogue": [{"speaker","text","emotion"}], "durationSeconds": 90 } },
 *   "nodeChoices": [ {"nodeId": "...", "nodeTitle": "兜底按标题匹配(须唯一)", "exploreReturnNodeId": "",
 *                     "choices": [{"text","targetNodeId","conditions","variableEffects","choiceWeight","consequence"}]} ],
 *   "ops": [ {"op": "add_node|update_node|add_choice|update_choice|set_explore_return|bind_ending",
 *             "target": {"nodeId": "..."} 或 {"nodeTitle": "..."}, "reason": "对应哪条 issue/mustFix",
 *             ...op 各自字段见下} ]
 * }
 *
 * ops 字段说明（定向修复用，只补不改写）：
 * - add_node:        node: {title, type(必填，六类之一), notes, sceneDesc?...}，插入到 target 节点之后（自动分配本章下一个可用 id）
 * - update_node:     patch: {title?, type?, notes?, notesAppend?}（只补/改这些字段，不清空其他内容）
 * - add_choice:      choice: {text, targetNodeId, conditions?, variableEffects?, choiceWeight?, consequence?}（追加到节点选项末尾；
 *                    若该选项带 conditions 且修后节点将没有任何无条件选项 → 拒绝）
 * - update_choice:   choiceIndex: 序号(0起) 或 matchText: 精确匹配现有选项文字；patch: {text?, targetNodeId?, conditions?, variableEffects?, choiceWeight?, consequence?}
 * - set_explore_return: value: "<exploreReturnNodeId>"
 * - bind_ending:     ending: {title, type(good/bad/neutral/secret), description?, conditions?, variableConditions?}（登记到 project.endings）
 *
 * 规则：只覆盖提供的字段，不触碰其他内容；choices 整组替换并自动补 order；
 *      targetNodeId / exploreReturnNodeId 必须指向已存在节点。
 */
const fs = require('fs');

const NODE_TYPES = ['start', 'normal', 'branch', 'merge', 'explore', 'ending'];
const ENDING_TYPES = ['good', 'bad', 'neutral', 'secret'];
const NODE_FIELDS = ['title', 'notes', 'sceneHeader', 'sceneDesc', 'emotionFunction', 'dialogue', 'durationSeconds'];
const CHOICE_FIELDS = ['text', 'targetNodeId', 'conditions', 'variableEffects', 'choiceWeight', 'consequence'];

const file = process.argv[2];
const payloadArg = process.argv[3];
if (!file || !fs.existsSync(file) || !payloadArg) {
  console.error('用法: alink scripts/fill-nodes.js <项目JSON路径> <填充JSON路径|->');
  process.exit(2);
}

let project;
try {
  project = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
  console.error('项目 JSON 解析失败: ' + e.message);
  process.exit(2);
}

let payload;
try {
  payload = JSON.parse(payloadArg === '-' ? fs.readFileSync(0, 'utf8') : fs.readFileSync(payloadArg, 'utf8'));
} catch (e) {
  console.error('填充 JSON 解析失败: ' + e.message);
  process.exit(2);
}

project.nodes = Array.isArray(project.nodes) ? project.nodes : [];
project.chapters = Array.isArray(project.chapters) ? project.chapters : [];
project.endings = Array.isArray(project.endings) ? project.endings : [];

const nodeById = new Map(project.nodes.map(n => [n.id, n]));
const titleCounts = new Map();
for (const n of project.nodes) titleCounts.set(n.title, (titleCounts.get(n.title) || 0) + 1);
const nodeByTitle = new Map(project.nodes.map(n => [n.title, n]));

// 解析节点引用：nodeId 优先；nodeTitle 兜底（重名时报错）
function resolveNode(ref) {
  if (!ref || (typeof ref !== 'object')) return { error: '缺少 target' };
  if (ref.nodeId) {
    const n = nodeById.get(ref.nodeId);
    return n ? { node: n } : { error: `不存在节点 ${ref.nodeId}` };
  }
  if (ref.nodeTitle) {
    if ((titleCounts.get(ref.nodeTitle) || 0) > 1) return { error: `nodeTitle「${ref.nodeTitle}」重名，请改用 nodeId` };
    const n = nodeByTitle.get(ref.nodeTitle);
    return n ? { node: n } : { error: `不存在标题为「${ref.nodeTitle}」的节点` };
  }
  return { error: 'target 缺少 nodeId / nodeTitle' };
}

const errors = [];
const stats = { chapters: 0, titles: 0, nodeContent: 0, choiceNodes: 0, choices: 0, ops: 0 };

// ── 预校验（任何错误 → 整批拒绝，不写盘）────────────────────────
for (const [order, patch] of Object.entries(payload.chapters || {})) {
  if (!project.chapters.some(c => Number(c.order) === Number(order))) errors.push(`chapters: 不存在 order=${order} 的章节记录`);
  else if (patch && typeof patch !== 'object') errors.push(`chapters[${order}]: 必须是对象`);
}

for (const [id, patch] of Object.entries(payload.titles || {})) {
  if (!nodeById.has(id)) { errors.push(`titles: 不存在节点 ${id}`); continue; }
  if (!patch || typeof patch !== 'object') { errors.push(`titles[${id}]: 必须是对象`); continue; }
  for (const k of Object.keys(patch)) if (k !== 'title' && k !== 'notes') errors.push(`titles[${id}]: 不允许的字段 "${k}"（仅 title/notes）`);
}

for (const [id, patch] of Object.entries(payload.nodeContent || {})) {
  if (!nodeById.has(id)) { errors.push(`nodeContent: 不存在节点 ${id}`); continue; }
  if (!patch || typeof patch !== 'object') { errors.push(`nodeContent[${id}]: 必须是对象`); continue; }
  for (const k of Object.keys(patch)) {
    if (!NODE_FIELDS.includes(k)) errors.push(`nodeContent[${id}]: 不允许的字段 "${k}"（白名单：${NODE_FIELDS.join('/')}）`);
  }
  if (patch.dialogue !== undefined) {
    if (!Array.isArray(patch.dialogue)) errors.push(`nodeContent[${id}].dialogue: 必须是数组`);
    else patch.dialogue.forEach((d, i) => {
      if (!d || typeof d !== 'object' || !String(d.speaker || '').trim() || !String(d.text || '').trim()) {
        errors.push(`nodeContent[${id}].dialogue[${i}]: 每行必须含 speaker 与 text`);
      }
    });
  }
  if (patch.durationSeconds !== undefined && !Number.isFinite(Number(patch.durationSeconds))) {
    errors.push(`nodeContent[${id}].durationSeconds 必须是数字`);
  }
}

for (const [ri, req] of (Array.isArray(payload.nodeChoices) ? payload.nodeChoices : []).entries()) {
  const { node, error } = resolveNode(req || {});
  if (error) { errors.push(`nodeChoices[${ri}]: ${error}`); continue; }
  if (req.exploreReturnNodeId !== undefined && req.exploreReturnNodeId !== '' && !nodeById.has(req.exploreReturnNodeId)) {
    errors.push(`nodeChoices[${ri}]（节点「${node.title}」）: exploreReturnNodeId "${req.exploreReturnNodeId}" 不存在`);
  }
  for (const [ci, c] of (req.choices || []).entries()) {
    if (!c || !String(c.text || '').trim()) errors.push(`nodeChoices[${ri}].choices[${ci}]: 缺 text`);
    if (!c || !c.targetNodeId || !nodeById.has(c.targetNodeId)) {
      errors.push(`nodeChoices[${ri}].choices[${ci}]: targetNodeId "${c && c.targetNodeId}" 不存在（必须从拓扑原样复制）`);
    }
    for (const k of Object.keys(c || {})) if (!CHOICE_FIELDS.includes(k)) errors.push(`nodeChoices[${ri}].choices[${ci}]: 不允许的字段 "${k}"`);
  }
}

// ── ops 预校验 ──────────────────────────────────────────────────
function checkChoiceShape(prefix, c) {
  if (!c || !String(c.text || '').trim()) errors.push(`${prefix}: 缺 text`);
  if (!c || !c.targetNodeId || !nodeById.has(c.targetNodeId)) errors.push(`${prefix}: targetNodeId "${c && c.targetNodeId}" 不存在`);
  for (const k of Object.keys(c || {})) if (!CHOICE_FIELDS.includes(k)) errors.push(`${prefix}: 不允许的字段 "${k}"`);
}

for (const [oi, op] of (Array.isArray(payload.ops) ? payload.ops : []).entries()) {
  const tag = `ops[${oi}](${op && op.op})`;
  if (!op || !NODE_TYPES.includes(op.op) && !['add_node', 'update_node', 'add_choice', 'update_choice', 'set_explore_return', 'bind_ending'].includes(op.op)) {
    errors.push(`${tag}: 未知 op "${op && op.op}"`); continue;
  }
  if (!String(op.reason || '').trim()) errors.push(`${tag}: 缺 reason（必须指明对应哪条 issue/mustFix）`);
  const { node, error } = resolveNode(op.target);
  if (error && op.op !== 'bind_ending') { errors.push(`${tag}: ${error}`); continue; }

  if (op.op === 'add_node') {
    const n = op.node || {};
    if (!NODE_TYPES.includes(n.type)) errors.push(`${tag}: node.type 必须是 ${NODE_TYPES.join('/')} 之一`);
    if (!String(n.title || '').trim()) errors.push(`${tag}: node.title 必填`);
    if (!String(n.notes || '').trim()) errors.push(`${tag}: node.notes 必填（须写明剧情意图：为什么加、承接什么、通向什么）`);
    for (const k of Object.keys(n)) if (k !== 'type' && !NODE_FIELDS.includes(k)) errors.push(`${tag}: node 不允许的字段 "${k}"`);
  } else if (op.op === 'update_node') {
    const p = op.patch || {};
    for (const k of Object.keys(p)) {
      if (!['title', 'type', 'notes', 'notesAppend'].includes(k)) errors.push(`${tag}: patch 不允许的字段 "${k}"`);
    }
    if (p.type !== undefined && !NODE_TYPES.includes(p.type)) errors.push(`${tag}: patch.type 非法`);
  } else if (op.op === 'add_choice') {
    checkChoiceShape(`${tag}.choice`, op.choice);
    if (node && op.choice && String(op.choice.conditions || '').trim()) {
      const cs = node.choices || [];
      const afterAdd = [...cs, op.choice];
      if (afterAdd.every(c => String(c.conditions || '').trim())) {
        errors.push(`${tag}: 该节点现有选项全部带条件，再加带条件的选项会触发 ALL_CHOICES_GATED——应先补无条件保底选项`);
      }
    }
  } else if (op.op === 'update_choice') {
    const cs = (node && node.choices) || [];
    let idx = -1;
    if (Number.isInteger(op.choiceIndex)) idx = op.choiceIndex;
    else if (op.matchText) idx = cs.findIndex(c => c.text === op.matchText);
    if (idx < 0 || idx >= cs.length) errors.push(`${tag}: 定位不到选项（choiceIndex=${op.choiceIndex} / matchText=${op.matchText}，该节点共 ${cs.length} 个选项）`);
    for (const k of Object.keys(op.patch || {})) if (!CHOICE_FIELDS.includes(k)) errors.push(`${tag}: patch 不允许的字段 "${k}"`);
    if (op.patch && op.patch.targetNodeId !== undefined && !nodeById.has(op.patch.targetNodeId)) errors.push(`${tag}: patch.targetNodeId "${op.patch.targetNodeId}" 不存在`);
  } else if (op.op === 'set_explore_return') {
    if (node && node.type !== 'explore') errors.push(`${tag}: 目标节点「${node.title}」不是 explore 类型`);
    if (!op.value || !nodeById.has(op.value)) errors.push(`${tag}: value "${op.value}" 不是已存在节点 id`);
  } else if (op.op === 'bind_ending') {
    const e = op.ending || {};
    if (!node || node.type !== 'ending') errors.push(`${tag}: target 必须是 ending 类型节点`);
    if (!String(e.title || '').trim()) errors.push(`${tag}: ending.title 必填`);
    if (!ENDING_TYPES.includes(e.type)) errors.push(`${tag}: ending.type 必须是 ${ENDING_TYPES.join('/')} 之一`);
  }
}

if (errors.length) {
  console.error(`填充被拒绝（${errors.length} 处错误，未写入任何内容）:`);
  for (const e of errors) console.error('  - ' + e);
  process.exit(1);
}

// ── 应用（只在预校验全过后执行）────────────────────────────────
for (const [order, patch] of Object.entries(payload.chapters || {})) {
  const c = project.chapters.find(x => Number(x.order) === Number(order));
  if (patch.title !== undefined) c.title = patch.title;
  stats.chapters++;
}
for (const [id, patch] of Object.entries(payload.titles || {})) {
  const n = nodeById.get(id);
  if (patch.title !== undefined) n.title = patch.title;
  if (patch.notes !== undefined) n.notes = patch.notes;
  stats.titles++;
}
for (const [id, patch] of Object.entries(payload.nodeContent || {})) {
  const n = nodeById.get(id);
  for (const k of NODE_FIELDS) if (patch[k] !== undefined) n[k] = patch[k];
  stats.nodeContent++;
}
for (const req of (Array.isArray(payload.nodeChoices) ? payload.nodeChoices : [])) {
  const { node } = resolveNode(req);
  if (req.exploreReturnNodeId !== undefined) node.exploreReturnNodeId = req.exploreReturnNodeId;
  if (req.choices) {
    node.choices = req.choices.map((c, i) => {
      const out = {};
      for (const k of CHOICE_FIELDS) if (c[k] !== undefined && c[k] !== '') out[k] = c[k];
      out.order = i + 1;
      return out;
    });
    stats.choiceNodes++;
    stats.choices += node.choices.length;
  }
}

// ── ops 应用 ───────────────────────────────────────────────────
// 章序号取自目标节点 id 前缀（c{n}…）
function chapterOfNode(n) {
  const m = /^c(\d+)/.exec(String(n.id || ''));
  return m ? Number(m[1]) : null;
}
function nextNodeIdInChapter(chapterNo) {
  let max = 0;
  const pre = `c${chapterNo}`;
  for (const n of project.nodes) {
    const m = new RegExp(`^${pre}n(\\d+)$`).exec(String(n.id));
    if (m) max = Math.max(max, Number(m[1]));
  }
  return `${pre}n${max + 1}`;
}

for (const op of (Array.isArray(payload.ops) ? payload.ops : [])) {
  const { node } = resolveNode(op.target);
  if (op.op === 'add_node') {
    const chapterNo = chapterOfNode(node) || 1;
    const id = nextNodeIdInChapter(chapterNo);
    const fresh = { id };
    for (const k of NODE_FIELDS) if (op.node[k] !== undefined) fresh[k] = op.node[k];
    fresh.type = op.node.type;
    // 插入到 target 节点之后：全局节点序列
    const at = project.nodes.findIndex(x => x.id === node.id);
    project.nodes.splice(at + 1, 0, fresh);
  } else if (op.op === 'update_node') {
    const p = op.patch || {};
    if (p.title !== undefined) node.title = p.title;
    if (p.type !== undefined) node.type = p.type;
    if (p.notes !== undefined) node.notes = p.notes;
    if (p.notesAppend) node.notes = node.notes ? `${node.notes}；${p.notesAppend}` : p.notesAppend;
  } else if (op.op === 'add_choice') {
    node.choices = Array.isArray(node.choices) ? node.choices : [];
    const out = {};
    for (const k of CHOICE_FIELDS) if (op.choice[k] !== undefined && op.choice[k] !== '') out[k] = op.choice[k];
    out.order = node.choices.length + 1;
    node.choices.push(out);
  } else if (op.op === 'update_choice') {
    const cs = node.choices || [];
    const idx = Number.isInteger(op.choiceIndex) ? op.choiceIndex : cs.findIndex(c => c.text === op.matchText);
    Object.assign(cs[idx], op.patch);
  } else if (op.op === 'set_explore_return') {
    node.exploreReturnNodeId = op.value;
  } else if (op.op === 'bind_ending') {
    project.endings.push({ nodeId: node.id, ...op.ending });
  }
  stats.ops++;
}

// add_node 可能改变序列，重排全局 order
project.nodes.forEach((n, i) => { n.order = i + 1; });

fs.writeFileSync(file, JSON.stringify(project, null, 2) + '\n');
console.log(JSON.stringify({ ok: true, written: file, ...stats }));
console.error(`已写入 ${file}：章节标题 ${stats.chapters}、节点 title/notes ${stats.titles}、内容节点 ${stats.nodeContent}、选项节点 ${stats.choiceNodes}（共 ${stats.choices} 个选项）、定向修复 ops ${stats.ops}。`);
