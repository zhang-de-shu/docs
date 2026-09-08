#!/usr/bin/env alink
/**
 * 逐章骨架搭建脚本（移植自原项目 lib/ai/prompts/structure.ts「structure:chapter」的骨架计算逻辑）
 *
 * 用法：alink scripts/build-skeleton.js <项目JSON路径> <章序号(从1起)>
 * 输入：项目 JSON（须已含 worldAnchor、scalePlan、characters、spine）
 * 输出：该章的骨架 JSON（acts/nodes 槽位与 type 已定，title/notes 为待 AI 填充的槽位提示），
 *       以及供 AI 填充时使用的硬约束摘要（stderr）。
 *
 * 设计说明：节点槽位与 type 全部由本脚本在代码层面精确计算（跨幕合并、BE 配额、
 * 幕结构模板、跨幕后处理），AI 只负责填充 title/notes——计数类工作不让模型做。
 */
const fs = require('fs');

const file = process.argv[2];
const chapterArg = Number(process.argv[3]);
if (!file || !fs.existsSync(file) || !Number.isInteger(chapterArg) || chapterArg < 1) {
  console.error('用法: alink scripts/build-skeleton.js <项目JSON路径> <章序号(从1起)>');
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
const chapterCount = Number(plan.chapterCount ?? 3);
const actCount = Number(plan.actCountPerChapter ?? 3);
const totalNodes = Number(plan.totalNodes ?? 25);
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

// ── 按规模方案推导本章/本幕节点数硬约束 ──────────────────────────
const chapterTargetNodes = Math.max(actCount * 2, Math.round(totalNodes / chapterCount));
const baseNodesPerAct = Math.floor(chapterTargetNodes / actCount);
const actRemainder = chapterTargetNodes - baseNodesPerAct * actCount;
const perActTarget = Array.from({ length: actCount }, (_, ai) => baseNodesPerAct + (ai < actRemainder ? 1 : 0));

// ── 跨幕合并：连续"预算<4"的非终章幕分组，组内最后一幕(host)合并全部预算搭完整菱形，
//    其余幕(donor)退化为 1 个纯推进节点；落单小预算幕并入相邻幕。终章末幕不参与合并。──
const isTerminalActIdx = (ai) => isLast && ai === actCount - 1;
const donorOf = new Array(actCount).fill(null);
const hostExtraBudget = new Array(actCount).fill(0);
{
  let i = 0;
  while (i < actCount) {
    if (isTerminalActIdx(i) || perActTarget[i] >= 4) { i++; continue; }
    let j = i;
    while (j < actCount && !isTerminalActIdx(j) && perActTarget[j] < 4) j++;
    if (j - i >= 2) {
      const host = j - 1;
      for (let k = i; k < host; k++) {
        donorOf[k] = host;
        hostExtraBudget[host] += perActTarget[k] - 1;
      }
    } else {
      const host = j < actCount && !isTerminalActIdx(j)
        ? j
        : (i - 1 >= 0 && !isTerminalActIdx(i - 1) && donorOf[i - 1] === null ? i - 1 : -1);
      if (host >= 0) {
        donorOf[i] = host;
        hostExtraBudget[host] += perActTarget[i] - 1;
      }
    }
    i = j;
  }
}

let chapterExploreUsed = false;
// 即死 BE 配额：终章 1 个；非终章章预算 ≥12 时 2 个、否则 1 个
const chapterBETarget = isLast ? 1 : (chapterTargetNodes >= 12 ? 2 : 1);
let chapterBEUsed = 0;
// 分支密度向后递增：后半段章降低平行路线预算门槛
const isLateChapter = chapterIndex >= Math.floor(chapterCount / 2);
const parallelThreshold = isLateChapter ? 6 : 8;

function buildActNodes(ai) {
  const isFirstAct = isFirst && ai === 0;
  const isLastActOfAll = isLast && ai === actCount - 1;
  const isDonorAct = donorOf[ai] !== null;
  const nodes = [];

  if (isFirstAct) {
    nodes.push({ title: '开场', type: 'start', notes: '主角登场，世界现状建立，触发事件' });
  } else if (isDonorAct) {
    nodes.push({ title: '节点名', type: 'normal', notes: `跨幕合并：本幕预算已并入第${donorOf[ai] + 1}幕用于搭建完整菱形分支，此处只承担剧情推进` });
  } else {
    nodes.push({ title: '节点名', type: 'normal', notes: '核心冲突推进' });
  }

  if (isLastActOfAll) {
    // 终章末幕：高潮 → 路线门控 → [路线专属场景, 结局] 交替排列
    nodes.push({ title: '最终时刻', type: 'normal', notes: '最黑暗时刻：所有矛盾在此爆发，此前积累的变量决定哪条路线对玩家开放' });
    nodes.push({ title: '路线门控', type: 'branch', notes: '根据全程积累的变量开放对应路线，每个选项的conditions字段必须填写具体变量条件（如affection_A>=3）' });
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
  } else if (isDonorAct) {
    // donor 幕：预算已转给 host，仅保留 entry 节点
  } else {
    const actSize = perActTarget[ai] + hostExtraBudget[ai];
    const budget = actSize - nodes.length;
    if (budget < 3) {
      const fillCount = Math.max(1, budget);
      for (let f = 0; f < fillCount; f++) {
        nodes.push({ title: '节点名', type: 'normal', notes: '剧情推进：聚焦人物关系或线索揭示，为后续张力做铺垫（本幕预算较小，暂不设关键分支）' });
      }
    } else if (actSize >= parallelThreshold) {
      // 章内平行路线
      const pathCount = Math.min(3, Math.max(2, endingsDesign.length || endingCount));
      const perPathNodes = Math.max(2, Math.floor((budget - 2) / pathCount));
      const includeBE = chapterBEUsed < chapterBETarget;
      nodes.push({ title: '节点名', type: 'branch', notes: `关键选择（章内平行路线）：${pathCount}条路径各自独立推进${perPathNodes}个节点后再汇回主线；每个选项必须填写variableEffects记录对变量的影响，且至少保留一个无条件保底选项${includeBE ? '；其中一条路径改为即死结局（BE），需给出一个有吸引力/危险诱惑的选项让玩家可能选中它' : ''}` });
      for (let p = 0; p < pathCount; p++) {
        const label = ['A', 'B', 'C'][p];
        if (includeBE && p === pathCount - 1) {
          nodes.push({ title: `路径${label}·即死结局`, type: 'ending', notes: `[路径${label}] 即死结局（BAD END）：死法必须呼应主角弱点或世界规则，是一次性格测验而非随机惩罚；短而有戏，有专属画面感` });
          continue;
        }
        for (let s = 0; s < perPathNodes; s++) {
          const hint = endingsDesign[p]
            ? `与「${endingsDesign[p].title}」结局相关的路线，第${s + 1}段：情节与其他路径明显不同`
            : `路径${label}第${s + 1}段：与此路线角色的专属场景，情节与其他路径明显不同`;
          nodes.push({ title: '节点名', type: 'normal', notes: `[路径${label}] ${hint}` });
        }
      }
      if (includeBE) chapterBEUsed++;
      const remainAfterPaths = actSize - nodes.length;
      if (remainAfterPaths >= 1) nodes.push({ title: '续接', type: 'merge', notes: '各路径汇回主线，故事继续向前推进' });
      if (!isLast && !chapterExploreUsed && chapterTargetNodes >= 10 && remainAfterPaths >= 2) {
        nodes.push({ title: '探索：槽位名', type: 'explore', notes: '可选隐藏内容：角色秘密、线索物品或世界背景' });
        chapterExploreUsed = true;
      }
    } else {
      // 标准菱形分支-汇合（预算 4-7）
      const maxPaths = Math.min(3, budget - 1);
      const pathCount = Math.min(Math.max(2, endingsDesign.length || endingCount), maxPaths);
      const includeBE = chapterBEUsed < chapterBETarget;
      nodes.push({ title: '节点名', type: 'branch', notes: `关键选择：${pathCount}条路径各有专属场景，结束后汇回；每个选项必须填写variableEffects记录对变量的影响，且至少保留一个无条件保底选项${includeBE ? '；其中一条路径改为即死结局（BE），需给出一个有吸引力/危险诱惑的选项让玩家可能选中它' : ''}` });
      for (let p = 0; p < pathCount; p++) {
        const label = ['A', 'B', 'C'][p];
        if (includeBE && p === pathCount - 1) {
          nodes.push({ title: `路径${label}·即死结局`, type: 'ending', notes: `[路径${label}] 即死结局（BAD END）：死法必须呼应主角弱点或世界规则，是一次性格测验而非随机惩罚；短而有戏，有专属画面感` });
          continue;
        }
        const hint = endingsDesign[p]
          ? `与「${endingsDesign[p].title}」结局相关的选择，affection或变量+1`
          : `路径${label}：与此路线角色的专属场景，情节与其他路径明显不同`;
        nodes.push({ title: '节点名', type: 'normal', notes: `[路径${label}] 路径入口：${hint}` });
        nodes.push({ title: '节点名', type: 'normal', notes: `[路径${label}] 路径深化：延续路径${label}的情节走向，与其他路径的差异要具体可感` });
      }
      if (includeBE) chapterBEUsed++;
      const remainAfterPaths = actSize - nodes.length;
      if (remainAfterPaths >= 1) nodes.push({ title: '续接', type: 'merge', notes: '各路径汇回主线，故事继续向前推进' });
      if (!isLast && !chapterExploreUsed && chapterTargetNodes >= 10 && remainAfterPaths >= 2) {
        nodes.push({ title: '探索：槽位名', type: 'explore', notes: '可选隐藏内容：角色秘密、线索物品或世界背景' });
        chapterExploreUsed = true;
      }
    }
  }

  // 补足到本幕目标节点数（donor 补到 1；结构下限超预算时保留结构完整性不强裁）
  const target = isDonorAct ? 1 : perActTarget[ai] + hostExtraBudget[ai];
  let guard = 0;
  while (nodes.length < target && guard < 30) {
    nodes.splice(1, 0, { title: '节点名', type: 'normal', notes: '剧情推进节点：补充本幕内容密度，承接前文并为后续做铺垫，可展开人物互动或信息揭示' });
    guard++;
  }
  return nodes;
}

const acts = Array.from({ length: actCount }, (_, ai) => ({
  title: `第${ai + 1}幕：幕名`,
  nodes: buildActNodes(ai),
}));

// ── 跨幕后处理（整章拼接后统一扫描）────────────────────────────
{
  const flat = [];
  acts.forEach((act, ai) => act.nodes.forEach((_, ni) => flat.push({ ai, ni })));
  const nodeAt = (ref) => acts[ref.ai].nodes[ref.ni];
  const appendNote = (node, extra) => {
    node.notes = node.notes ? `${node.notes}；${extra}` : extra;
  };
  // merge 之后的第一个节点：按路线变量写差异化开场台词
  flat.forEach((ref, idx) => {
    const node = nodeAt(ref);
    if (node.type !== 'merge') return;
    const nextRef = flat[idx + 1];
    appendNote(nextRef ? nodeAt(nextRef) : node, '开场台词必须按玩家来路（本幕路线变量）写出差异化版本');
  });
  // 本章最后一个非 ending 节点：章末钩子（终章不加）
  if (!isLast) {
    for (let idx = flat.length - 1; idx >= 0; idx--) {
      const node = nodeAt(flat[idx]);
      if (node.type !== 'ending') {
        appendNote(node, '本章末钩子：以悬念/反转/倒计时收束，给观众继续看下一章的理由');
        break;
      }
    }
  }
}

const actualNodeCounts = acts.map(a => a.nodes.length);
const actualChapterTotal = actualNodeCounts.reduce((s, n) => s + n, 0);

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
  skeleton: { title: chapterOutline[chapterIndex]?.title ?? `第${chapterIndex + 1}章`, acts },
  constraint: {
    totalNodes, chapterCount, actCount, chapterTargetNodes, actualChapterTotal,
    actualNodeCounts,
    incomingHandoff: incomingHandoff?.carry_over ?? null,
    outgoingHandoff: outgoingHandoff?.carry_over ?? null,
    chapterArcs: chapterArcs || null,
    throughlines: spine.throughlines || [],
    position: `第${chapterIndex + 1}章 / 共${chapterCount}章${isFirst ? '（开篇：建立世界、触发事件、第一个道德选择）' : ''}${isLast ? '（终章：最黑暗时刻 → 内心蜕变 → 最终抉择 → 多结局）' : ''}`,
  },
};

console.log(JSON.stringify(result, null, 2));
console.error(`骨架就绪：本章目标 ${chapterTargetNodes} 节点，实际 ${actualChapterTotal} 节点（逐幕：${actualNodeCounts.join('，')}）。AI 填充时节点数量/顺序/type 不可更改，仅替换 title/notes。`);
