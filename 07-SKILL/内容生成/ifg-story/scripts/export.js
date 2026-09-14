#!/usr/bin/env alink
/**
 * 导出脚本（Markdown 剧本 / ink / JSON）
 *
 * 用法：
 *   alink scripts/export.js <项目JSON路径> <输出目录> [--ink]
 * 默认导出 Markdown 剧本 + 完整 JSON；--ink 额外导出 .ink 文本。
 * ink 导出规则见 references/ink-export.md（源自原项目 lib/persistence.ts exportInk）。
 */
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const file = args[0];
const outDir = args[1];
const wantInk = args.includes('--ink');
if (!file || !fs.existsSync(file) || !outDir) {
  console.error('用法: alink scripts/export.js <项目JSON路径> <输出目录> [--ink]');
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
const chapters = project.chapters || [];
const endings = project.endings || [];

fs.mkdirSync(outDir, { recursive: true });

// ── Markdown 剧本（章 → 节点 两级）─────────────────────────────
const nodesByChapter = new Map();
for (const ch of chapters) nodesByChapter.set(ch.id || `order:${ch.order}`, []);
// 章内节点顺序：按 id 前缀（c{order} → c{order}n*）+ 全局 nodes 顺序
for (const ch of chapters) {
  const key = ch.id || `order:${ch.order}`;
  const ordered = [];
  const seen = new Set();
  const prefix = (ch.id || '').replace(/[^a-z0-9]/gi, '') || `c${ch.order}`;
  for (const n of nodes) {
    if (String(n.id).startsWith(prefix) && !seen.has(n.id)) { ordered.push(n); seen.add(n.id); }
  }
  nodesByChapter.set(key, ordered);
}

const mdLines = [];
mdLines.push(`# ${project.title || '互动影游'}\n`);
if (project.worldAnchor?.storyCore) mdLines.push(`> ${project.worldAnchor.storyCore}\n`);

const sortedChapters = [...chapters].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
for (const ch of sortedChapters) {
  mdLines.push(`## ${ch.title}\n`);
  const key = ch.id || `order:${ch.order}`;
  const chNodes = nodesByChapter.get(key) || [];
  for (const n of chNodes) {
    const beTag = n.type === 'ending' && (endings.find(e => e.nodeId === n.id)?.type === 'bad') ? ' **【BE】**' : '';
    mdLines.push(`### ${n.title}${beTag}\n`);
    if (n.sceneHeader) {
      const sh = n.sceneHeader;
      mdLines.push(`**${sh.interior || ''} ${sh.location || ''} — ${sh.timeOfDay || ''}**\n`);
    }
    if (n.notes) mdLines.push(`> 创作备注：${n.notes}\n`);
    if (n.sceneDesc) mdLines.push(`${n.sceneDesc}\n`);
    for (const d of n.dialogue || []) {
      mdLines.push(`**${d.speaker}**（${d.emotion || ''}）：${d.text}`);
    }
    if ((n.dialogue || []).length) mdLines.push('');
    for (const c of n.choices || []) {
      const parts = [];
      if (c.conditions) parts.push(`条件: ${c.conditions}`);
      if (c.variableEffects) parts.push(`效果: ${c.variableEffects}`);
      const meta = parts.length ? `（${parts.join('；')}）` : '';
      const target = nodeById.get(c.targetNodeId);
      mdLines.push(`- ▶ ${c.text}${meta}${target ? ` → ${target.title}` : ''}`);
    }
    if ((n.choices || []).length) mdLines.push('');
    if (n.type === 'explore' && n.exploreReturnNodeId) {
      const ret = nodeById.get(n.exploreReturnNodeId);
      mdLines.push(`- ↩ 探索结束返回${ret ? `：${ret.title}` : ''}\n`);
    }
    if (n.durationSeconds) mdLines.push(`*时长约 ${n.durationSeconds} 秒*\n`);
  }
}
fs.writeFileSync(path.join(outDir, '剧本.md'), mdLines.join('\n'), 'utf-8');

// ── JSON（事实来源）─────────────────────────────────────────────
fs.writeFileSync(path.join(outDir, 'project.json'), JSON.stringify(project, null, 2), 'utf-8');

// ── ink（可选）─────────────────────────────────────────────────
if (wantInk) {
  // 变量名净化
  const varNameMap = new Map();
  let hashCounter = 0;
  const sanitizeVar = (name) => {
    if (varNameMap.has(name)) return varNameMap.get(name);
    let conv = name.replace(/[^a-zA-Z0-9_]/g, '_');
    if (/^[0-9]/.test(conv)) conv = 'var_' + conv;
    if (!conv) conv = 'var_' + (++hashCounter);
    varNameMap.set(name, conv);
    return conv;
  };

  // 收集所有已声明变量 + 正文实际引用但未登记的变量（自洽铁律：补齐 VAR 声明）
  const declared = new Set((project.variables || []).map(v => v.name));
  const referenced = new Map(); // name -> {setString:boolean}
  const EFFECT_RE = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\+|-|=)\s*(.+?)\s*$/;
  for (const n of nodes) {
    for (const c of n.choices || []) {
      if (c.variableEffects) {
        for (const part of c.variableEffects.split(/[,，]/)) {
          const m = EFFECT_RE.exec(part.replace(/^\+/, m2 => m2.slice(1)) || '');
          const m2 = EFFECT_RE.exec(part.trim().replace(/^\+/, ''));
          const mm = m2 || m;
          if (mm) referenced.set(mm[1], referenced.get(mm[1]) || { setString: mm[2] === '=' && !/^\d+$/.test(mm[3]) });
        }
      }
      // conditions 中引用的变量由解析器提取
      if (c.conditions) {
        for (const vm of c.conditions.matchAll(/[A-Za-z_][A-Za-z0-9_]*/g)) {
          if (['&&', '||'].includes(vm[0])) continue;
          referenced.set(vm[0], referenced.get(vm[0]) || { setString: false });
        }
      }
    }
  }

  const inkLines = [];
  inkLines.push(`// ${project.title || '互动影游'}`);
  inkLines.push(`// 互动影游导出 · ${new Date().toISOString().slice(0, 10)}`);
  inkLines.push('');

  // VAR 声明
  const varDefaults = new Map();
  for (const v of project.variables || []) varDefaults.set(v.name, v.defaultValue ?? 0);
  for (const [name, info] of referenced) {
    if (!varDefaults.has(name)) varDefaults.set(name, info.setString ? '""' : 0);
  }
  for (const [name, def] of varDefaults) {
    const conv = sanitizeVar(name);
    const value = typeof def === 'string' && !/^[-\d]/.test(def) ? `"${def}"` : def;
    inkLines.push(`VAR ${conv} = ${value}`);
    if (conv !== name) inkLines.push(`// 变量映射: ${conv} = "${name}"`);
  }
  inkLines.push('');

  // knot 名净化
  const knotMap = new Map();
  const knotOf = (n) => {
    if (knotMap.has(n.id)) return knotMap.get(n.id);
    let base = (n.title || n.id).replace(/[^a-zA-Z0-9_一-龥]/g, '_');
    let knot = base;
    let k = 2;
    while ([...knotMap.values()].includes(knot)) knot = base + '_' + (k++);
    knotMap.set(n.id, knot);
    return knot;
  };

  // 条件转换：保留括号与 &&/|| 结构，变量名净化；无法解析的子式丢弃（退化为无条件）
  const convertCond = (cond) => {
    if (!cond || !cond.trim()) return null;
    return cond
      .replace(/[A-Za-z_][A-Za-z0-9_]*/g, w => ['&&', '||'].includes(w) || /^\d/.test(w) ? w : sanitizeVar(w))
      .replace(/&&/g, ' and ')
      .replace(/\|\|/g, ' or ');
  };

  const choicesOf = (n) => n.choices || [];
  for (const n of nodes) {
    inkLines.push(`=== ${knotOf(n)} ===`);
    if (n.sceneDesc) inkLines.push(n.sceneDesc.replace(/\n/g, ' '));
    for (const d of n.dialogue || []) {
      inkLines.push(`${d.speaker}：${d.text}`);
    }
    if (n.type === 'ending') {
      inkLines.push('->->');
      inkLines.push('');
      continue;
    }
    if (n.type === 'explore' && n.exploreReturnNodeId && nodeById.has(n.exploreReturnNodeId)) {
      inkLines.push(`-> ${knotOf(nodeById.get(n.exploreReturnNodeId))}`);
      inkLines.push('');
      continue;
    }
    const cs = choicesOf(n);
    if (cs.length === 0) {
      inkLines.push('-> DONE');
      inkLines.push('');
      continue;
    }
    for (const c of cs) {
      if (!c.targetNodeId || !nodeById.has(c.targetNodeId)) continue;
      const target = nodeById.get(c.targetNodeId);
      // variableEffects → ink set 行
      if (c.variableEffects) {
        for (const part of c.variableEffects.split(/[,，]/)) {
          const mm = EFFECT_RE.exec(part.trim().replace(/^\+/, ''));
          if (!mm) continue;
          const v = sanitizeVar(mm[1]);
          if (mm[2] === '=') {
            inkLines.push(`~ ${v} = ${/^\d+$/.test(mm[3]) ? mm[3] : `"${mm[3]}"`}`);
          } else if (mm[2] === '+') {
            inkLines.push(`~ ${v} = ${v} + ${mm[3] || 1}`);
          } else {
            inkLines.push(`~ ${v} = ${v} - ${mm[3] || 1}`);
          }
        }
      }
      const cond = convertCond(c.conditions);
      if (cond) {
        inkLines.push(`+ [${c.text}] { ${cond} }: -> ${knotOf(target)}`);
      } else {
        inkLines.push(`+ [${c.text}] -> ${knotOf(target)}`);
      }
    }
    // 兜底跳转（保底出口保证可达）
    const last = cs[cs.length - 1];
    if (last && !last.conditions && last.targetNodeId && nodeById.has(last.targetNodeId)) {
      // 最后一个无条件选项已是天然兜底
    } else {
      const fallback = cs.map(c => c.targetNodeId).map(id => nodeById.get(id)).filter(Boolean)[0];
      if (fallback) inkLines.push(`-> ${knotOf(fallback)}`);
    }
    inkLines.push('');
  }

  // start knot 跳转入口
  const startNode = nodes.find(n => n.type === 'start');
  if (startNode) {
    inkLines.unshift(`-> ${knotOf(startNode)}`, '');
  }

  fs.writeFileSync(path.join(outDir, 'story.ink'), inkLines.join('\n'), 'utf-8');
}

console.log(`导出完成：${path.join(outDir, '剧本.md')}、${path.join(outDir, 'project.json')}${wantInk ? `、${path.join(outDir, 'story.ink')}` : ''}`);
