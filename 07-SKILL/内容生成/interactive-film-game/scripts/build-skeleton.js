#!/usr/bin/env alink
/**
 * 逐章骨架搭建脚本
 *
 * 用法：alink scripts/build-skeleton.js <项目JSON路径> <章序号(从1起)> [--write]
 * 输入：项目 JSON（须已含 worldAnchor、scalePlan、characters、spine）
 * 输出：该章的骨架 JSON（nodes 槽位与 type 已定，节点含确定性 id，title/notes 为待 AI 填充的槽位提示），
 *       以及供 AI 填充时使用的硬约束摘要（stderr）。
 * 加 --write 时：把本章骨架（章节记录与节点）直接合并写入项目 JSON（幂等：重跑仅替换本章），
 *   stdout 仍打印骨架供 AI 填充；不加时只打印不写盘。
 *
 * 结构分层（对齐 domain-baseline.md）：章 → 小节（节点）两级，没有幕层。
 * - 章是叙事单元，每章 20-30 个节点（含 BE 小节）
 * - 即死 BE 岔口：每章 4-8 个（占选择节点 20-30%）
 * - 第 1 章必须出现首个即死 BE（选择即后果教学）
 */
const fs = require('fs');

const file = process.argv[2];
const chapterArg = Number(process.argv[3]);
const writeBack = process.argv.includes('--write');
if (!file || !fs.existsSync(file) || !Number.isInteger(chapterArg) || chapterArg < 1) {
  console.error('用法: alink scripts/build-skeleton.js <项目JSON路径> <章序号(从1起)> [--write]');
  process.exit(2);
}

let project;
try {
  project = JSON.parse(fs.readFileSync(file, 'utf8'));
} catch (e) {
  console.error('JSON 解析失败: ' + e.message);
  process.exit(2);
}

const plan = project.scalePlan || {};
const world = project.worldAnchor || {};
const spine = project.spine || {};
const chapterCount = Number(plan.chapterCount ?? 5);
// 每章节点数：优先读 nodesPerChapter；兼容旧字段按 totalNodes/chapterCount 推导；下限 20、上限 30
const nodesPerChapterRaw = Number(plan.nodesPerChapter ?? 0)
  || (Number(plan.totalNodes ?? 0) > 0 ? Math.round(Number(plan.totalNodes) / chapterCount) : 0)
  || 25;
const nodesPerChapter = Math.max(10, Math.min(30, nodesPerChapterRaw)); // 短剧档（1-2章）允许 10-15
const chapterIndex = chapterArg - 1;
const endingCount = Number(world.endingCount ?? 2);
const chapterOutline = plan.chapters || [];

if (chapterIndex >= chapterCount) {
  console.error(`章序号超界：共 ${chapterCount} 章`);
  process.exit(2);
}

const isFirst = chapterIndex === 0;
const isLast = chapterIndex === chapterCount - 1;
const endingsDesign = world.endingsDesign || [];

// ── 即死 BE 配额：每章 4-8 个（占选择节点 20-30%）──────────────────
// 章越大配额越高；第 1 章保底 4 个（选择即后果教学）；终章略降（结局路线为主）
function beQuotaFor(nodesTarget) {
  if (isLast) return Math.max(3, Math.min(6, Math.round(nodesTarget * 0.15)));
  const base = Math.max(4, Math.round(nodesTarget * 0.2));
  return Math.min(8, Math.max(4, base));
}
const chapterBETarget = beQuotaFor(nodesPerChapter);
let chapterBEUsed = 0;

// ── 章内结构预算 ──────────────────────────────────────────────────
// 非终章模板（按预算自适应，最终用 trimToTarget 裁齐到目标节点数）：
//   承接/start → [推进节点(2-3) + 散布BE] → 菱形分岔(含BE路径) → merge → …
// 终章：高潮 → (1个BE) → 路线门控 → [路线专属场景, 结局] × endingCount
const nodes = [];

// 章首节点
if (isFirst) {
  nodes.push({ title: '开场', type: 'start', notes: '主角登场，世界现状建立，触发事件；本章内必须出现首个即死 BE 和首个可感知的变量写入（选择即后果教学）' });
} else {
  nodes.push({ title: '承接', type: 'normal', notes: '承接上章钩子开场即冲突，按 handoff 写明主角携带的处境变化' });
}

// BE 插入器：确定性间隔散布（不取随机）
function beGapInterval() { return Math.max(3, Math.floor((nodesPerChapter - 10) / Math.max(1, chapterBETarget))); }
let beGapCounter = 0;
function maybeBE(extraNotes, force) {
  if (chapterBEUsed >= chapterBETarget) return false;
  if (!force) {
    beGapCounter++;
    if (chapterBEUsed >= 1 && beGapCounter < beGapInterval()) return false;
  }
  beGapCounter = 0;
  chapterBEUsed++;
  nodes.push({
    title: `即死岔口${chapterBEUsed}（BE）`, type: 'branch',
    notes: `性格测验节点（即死 BE 岔口 ${chapterBEUsed}/${chapterBETarget}）：错误选项直达 BAD END——这条路线的故事到此为止（暴露/任务失败/关系崩塌/被驱逐/身死皆可，即死不等于真死）。恶果呼应主角 fatalFlaw 弱点（${extraNotes || '如：多嘴/轻信/优柔寡断/杀伐果断'}），是性格测验而非随机惩罚。BE 选项文案必须有吸引力/危险诱惑、不能一眼看出死路，且不写 variableEffects（选中即终结）`,
  });
  nodes.push({
    title: `即死结局${chapterBEUsed}（BE）`, type: 'ending',
    notes: `BAD END 专属场景：短而有戏、有专属画面感（不是黑屏），恶果形式与上一个岔口的选择构成因果；结尾留一句"如果当时……"式回溯钩子`,
  });
  return true;
}

if (isLast) {
  // ── 终章：推进段(含BE) → 高潮 → 门控 → [专属场景, 结局]×N ──────
  // 终章前段补推进节点，把 BE 配额填满（终章中段同样高危）
  while (chapterBEUsed < chapterBETarget) {
    if (!maybeBE('终章高压下的失误', true)) break;
    nodes.push({ title: '节点名', type: 'normal', notes: '剧情推进：聚焦人物关系或线索揭示，为最终爆发蓄力；此节点须有 2-3 个真选择（同目标不同语气/变量效果）' });
  }
  nodes.push({ title: '最终时刻', type: 'normal', notes: '最黑暗时刻：所有矛盾在此爆发，此前积累的变量决定哪条路线对玩家开放' });
  nodes.push({ title: '路线门控', type: 'branch', notes: '根据全程积累的变量开放对应路线，每个选项的 conditions 必须填写具体变量条件（如 affection_A>=3）；只开放玩家"挣来的"结局路线，未满足条件的选项不可见' });
  const actualEndingCount = Math.max(2, endingCount);
  for (let e = 0; e < actualEndingCount; e++) {
    const design = endingsDesign[e];
    nodes.push({
      title: `${design?.title ?? `路线${e + 1}`}·专属场景`,
      type: 'normal',
      notes: design
        ? `【路线${e + 1}专属内容】条件：${design.triggerCondition}；写此路线玩家才能看到的场景、对话和情感时刻`
        : `【路线${e + 1}专属内容】只有满足此路线条件的玩家才能看到的场景`,
    });
    nodes.push({
      title: design?.title ?? `结局${e + 1}`,
      type: 'ending',
      notes: design ? `${design.type}结局：${design.triggerCondition}` : `结局${e + 1}`,
    });
  }
} else {
  // ── 非终章：菱形分岔数量按预算定，推进节点填充到目标 ────────────
  // 每个菱形占用约 5 个槽位（branch + 2路径×2节点 + merge），先按预算算个数
  const diamondCount = Math.max(3, Math.floor((nodesPerChapter - 6) / 5));
  const segments = [];
  for (let d = 0; d < diamondCount; d++) {
    const includeBE = chapterBEUsed < chapterBETarget;
    const items = [];
    items.push({
      title: '节点名', type: 'branch',
      notes: `关键选择（菱形分岔 ${d + 1}/${diamondCount}）：2-3 条路径各有专属场景，结束后汇回主线；每个选项必须填写 variableEffects 记录对变量的影响，且至少保留一个无条件保底选项${includeBE ? '；其中一条路径改为即死结局（BE），需给出一个有吸引力/危险诱惑的选项让玩家可能选中它' : ''}`,
    });
    const pathCount = 2;
    for (let p = 0; p < pathCount; p++) {
      const label = ['A', 'B'][p];
      if (includeBE && p === pathCount - 1) {
        items.push({ title: `路径${label}·即死结局`, type: 'ending', notes: `[路径${label}] 即死结局（BAD END）：这条路线的故事到此为止（暴露/失败/崩塌/被逐/身死皆可，即死不等于真死），恶果必须呼应主角 fatalFlaw 弱点，是一次性格测验而非随机惩罚；短而有戏，有专属画面感` });
        continue;
      }
      items.push({ title: '节点名', type: 'normal', notes: `[路径${label}] 路径入口：与此路线角色的专属场景，情节与其他路径明显不同` });
      items.push({ title: '节点名', type: 'normal', notes: `[路径${label}] 路径深化：延续路径${label}的情节走向，与其他路径的差异要具体可感` });
    }
    if (includeBE) chapterBEUsed++;
    items.push({ title: '续接', type: 'merge', notes: '各路径汇回主线，故事继续向前推进；下一节点开场台词必须按玩家来路（本段路线变量）写出差异化版本' });
    segments.push({ items });
  }

  // 组装：段间填充推进节点与散布 BE，至目标预算（-1 留给可能的探索节点）
  const budget = nodesPerChapter - 1; // 预留 1 个 explore 槽位
  let exploreUsed = false;
  for (let s = 0; s < segments.length && nodes.length < budget; s++) {
    // 段前推进节点：填到"加上本段后仍不超预算"为止
    const room = budget - nodes.length - segments[s].items.length;
    const preAdvance = Math.max(0, Math.min(s === 0 ? 2 : 3, room));
    for (let a = 0; a < preAdvance; a++) {
      maybeBE();
      nodes.push({ title: '节点名', type: 'normal', notes: '剧情推进：聚焦人物关系或线索揭示，为后续张力做铺垫；此节点须有 2-3 个真选择（同目标不同语气/变量效果）' });
    }
    for (const it of segments[s].items) nodes.push(it);
    // 探索节点（全章 1 个，段间）
    if (!exploreUsed && nodesPerChapter >= 15 && s < segments.length - 1 && nodes.length < budget) {
      nodes.push({ title: '探索：槽位名', type: 'explore', notes: '可选支线（不卡主线）：角色秘密、线索物品或世界背景，是世界活着的证据' });
      exploreUsed = true;
    }
  }
  // 末尾推进段补足剩余预算（可再散布 BE）
  while (nodes.length < budget) {
    maybeBE();
    nodes.push({ title: '节点名', type: 'normal', notes: '剧情推进：聚焦人物关系或线索揭示，为后续张力做铺垫；此节点须有 2-3 个真选择（同目标不同语气/变量效果）' });
  }
  // 预算有余量时补探索节点
  if (!exploreUsed && nodesPerChapter >= 15 && nodes.length < nodesPerChapter) {
    nodes.push({ title: '探索：槽位名', type: 'explore', notes: '可选支线（不卡主线）：角色秘密、线索物品或世界背景，是世界活着的证据' });
  }
}

// 章末钩子（终章不加）
if (!isLast) {
  const lastNonEnding = [...nodes].reverse().find(n => n.type !== 'ending');
  if (lastNonEnding) {
    lastNonEnding.notes = lastNonEnding.notes
      ? `${lastNonEnding.notes}；本章末钩子：以悬念/反转/倒计时收束，给观众继续看下一章的理由`
      : '本章末钩子：以悬念/反转/倒计时收束，给观众继续看下一章的理由';
  }
}

// ── 节点 id / 章节组装（章 → 节点 两级，无幕层）─────────────────────
const chapterId = `c${chapterIndex + 1}`;
nodes.forEach((n, ni) => {
  n.id = `${chapterId}n${ni + 1}`;
});

function chapterRecord() {
  return {
    order: chapterIndex + 1,
    title: chapterOutline[chapterIndex]?.title ?? `第${chapterIndex + 1}章：章名`,
  };
}

// 重建全局节点序列：按章节顺序拼接各章节点（本章用新节点替换旧节点），保证数组顺序 = 叙事顺序
function rebuildNodes(proj) {
  const chapOfId = (id) => { const m = /^c(\d+)n\d+$/.exec(String(id)) || /^c(\d+)a\d+n\d+$/.exec(String(id)); return m ? Number(m[1]) : null; };
  const byChapter = new Map();
  const stray = [];
  for (const n of proj.nodes || []) {
    const co = chapOfId(n.id);
    if (co === null) { stray.push(n); continue; }
    if (!byChapter.has(co)) byChapter.set(co, []);
    byChapter.get(co).push(n);
  }
  byChapter.set(chapterIndex + 1, nodes);
  const flat = [];
  for (const co of [...byChapter.keys()].sort((x, y) => x - y)) flat.push(...byChapter.get(co));
  if (stray.length) console.error(`警告：发现 ${stray.length} 个非脚本命名的既有节点，已追加到节点序列末尾`);
  flat.push(...stray);
  flat.forEach((n, i) => { n.order = i + 1; });
  return flat;
}

if (writeBack) {
  project.chapters = Array.isArray(project.chapters) ? project.chapters : [];
  project.nodes = Array.isArray(project.nodes) ? project.nodes : [];
  const record = chapterRecord();
  const oldIdx = project.chapters.findIndex(c => Number(c.order) === chapterIndex + 1);
  if (oldIdx >= 0) project.chapters[oldIdx] = record;
  else {
    const at = project.chapters.findIndex(c => Number(c.order) > chapterIndex + 1);
    if (at >= 0) project.chapters.splice(at, 0, record);
    else project.chapters.push(record);
  }
  project.nodes = rebuildNodes(project);
  fs.writeFileSync(file, JSON.stringify(project, null, 2) + '\n');
}

// 骨干上下文（供填充提示词引用）
const handoffs = spine.chapter_handoffs || [];
const incomingHandoff = handoffs.find(h => h.to === chapterIndex + 1);
const outgoingHandoff = handoffs.find(h => h.from === chapterIndex + 1);
const charArcs = spine.character_arcs || {};
const chapterArcs = Object.entries(charArcs)
  .map(([name, arc]) => `${name}：${arc[chapterIndex] ?? ''}`)
  .filter(s => s.includes('：') && s.split('：')[1])
  .join('  |  ');

const result = {
  chapter: chapterOutline[chapterIndex]?.title ?? `第${chapterIndex + 1}章`,
  skeleton: { title: chapterOutline[chapterIndex]?.title ?? `第${chapterIndex + 1}章`, nodes },
  written: writeBack ? { file, chapterId, nodeCount: nodes.length } : null,
  constraint: {
    chapterCount, nodesPerChapter, actualChapterTotal: nodes.length,
    beTarget: chapterBETarget, beActual: chapterBEUsed,
    beRatio: `${Math.round(chapterBEUsed / Math.max(1, nodes.filter(n => n.type !== 'ending').length) * 100)}%`,
    incomingHandoff: incomingHandoff?.carry_over ?? null,
    outgoingHandoff: outgoingHandoff?.carry_over ?? null,
    chapterArcs: chapterArcs || null,
    throughlines: spine.throughlines || [],
    position: `第${chapterIndex + 1}章 / 共${chapterCount}章${isFirst ? '（开篇：建立世界、触发事件、首个即死 BE 与首个变量写入）' : ''}${isLast ? '（终章：最黑暗时刻 → 变量门控 → 专属路线 → 多结局扇出）' : ''}`,
  },
};

console.log(JSON.stringify(result, null, 2));
console.error(`骨架就绪：本章目标 ${nodesPerChapter} 节点，实际 ${nodes.length} 节点；即死 BE ${chapterBEUsed}/${chapterBETarget}。${writeBack ? `已写入 ${file}（重跑幂等，仅替换本章）。` : '未写盘（加 --write 直接写入项目 JSON）。'}AI 填充：alink scripts/fill-nodes.js <项目JSON路径> <填充JSON路径>（{"chapters":..,"titles":{nodeId:{title,notes}}}）；节点数量/顺序/type 不可更改，仅替换 title/notes。`);
