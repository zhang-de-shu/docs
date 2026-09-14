#!/usr/bin/env node
/**
 * 图片生成脚本（单图 + 批量编排一体，现成完整——禁止现场另写生成/调用代码）
 *
 * 单图模式（手动重绘/补拍单张）：
 *   node gen_batch.mjs --prompt "..." --ref a.png,b.jpg --out images/nodes/c1/c1n3.jpg [--qc]
 *   node gen_batch.mjs --prompt-file p.txt --out out.png
 *
 * 批量模式 A：manifest（场景底图 + 节点图，自动记账、断点续跑）：
 *   node gen_batch.mjs --manifest <项目目录>/images/manifest.json \
 *        [--group scenes|nodes] [--filter c1] [--status prompt_confirmed,failed] \
 *        [--limit N] [--qc] [--interval-ms 2000] [--force]
 *   槽位 = manifest.scenes / manifest.nodes 条目的 { prompt, refs, path }（+ status）
 *
 * 批量模式 B：tasks（角色设定卡 / 封面等临时清单，不记账）：
 *   node gen_batch.mjs --tasks tasks.json [--base <项目目录>] [--qc] [--interval-ms 2000] [--force]
 *   tasks.json = [{ "id": "sheet-林秋", "prompt": "...", "refs": ["images/....png"], "out": "images/sheets/林秋.png" }]
 *   槽位 = 每项的 { prompt, refs, out }
 *
 * 配置（优先级：命令行 > 环境变量 > 默认）：
 *   --key ZENMUX_API_KEY | --model ZENMUX_IMAGE_MODEL（默认 google/gemini-2.5-flash-image）| --base-url ZENMUX_BASE_URL
 *   协议自动路由：google/* → vertex-ai generateContent；openai/* → images/generations|edits；其他 → vertex-ai :predict
 *   本机走代理时需 NODE_OPTIONS="--require <skill>/scripts/proxy-preload.cjs"（Node fetch 默认不走 HTTP(S)_PROXY）
 *
 * 内置硬约束（与 SKILL.md 一致）：
 *   - 串行生成，默认间隔 2s（防网关限流），不并发
 *   - **默认每次最多生成 10 张**（--limit 覆盖；--limit 0 = 不限量），跑完一批向用户确认后再跑下一批；
 *     被 limit 截断的项留在队列外，重跑同一命令自动接上
 *   - 跳过已生成：输出文件已存在（且非 rejected/--force）→ 不再调用图像模型；重复执行/中断续跑安全
 *   - HTTP 402（余额/配额耗尽）→ 立即停止整批，退出码 5；续跑重跑同一命令即可
 *   - 其他失败连续 3 次 → 停止，退出码 6
 *   - manifest 模式：先写图、后写 manifest（tmp+rename 原子落盘），每张实时置 done/failed
 *
 * 退出码：0 成功（含跳过）| 1 用法错误 | 2 有失败项/HTTP 错误 | 3 响应无图 | 4 异常 | 5 = HTTP 402 整批停止 | 6 = 连续失败停止
 */
import fs from 'fs'
import path from 'path'

function arg(name, def) { const i = process.argv.indexOf('--' + name); return i >= 0 ? process.argv[i + 1] : def }
const flag = (name) => process.argv.includes('--' + name)

const KEY = arg('key') || process.env.ZENMUX_API_KEY || ''
const MODEL = arg('model') || process.env.ZENMUX_IMAGE_MODEL || 'google/gemini-2.5-flash-image'
const BASE_URL = (arg('base-url') || process.env.ZENMUX_BASE_URL || 'https://zenmux.ai/api/v1').replace(/\/$/, '')
const VERTEX_BASE = 'https://zenmux.ai/api/vertex-ai'
const CHAT_MODEL = arg('chat-model') || process.env.ZENMUX_CHAT_MODEL || 'google/gemini-2.5-flash'
const TIMEOUT_MS = 180_000
const QC = flag('qc')

// ——— 单图生成核心（返回退出码语义：0 成功 | 2 HTTP 错误 | 3 无图 | 4 异常 | 5 = 402） ———
function loadRefs(refPaths) {
  return refPaths.filter(Boolean).map((p) => {
    const buf = fs.readFileSync(p)
    const ext = path.extname(p).slice(1).toLowerCase()
    const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'webp' ? 'image/webp' : ext === 'gif' ? 'image/gif' : 'image/png'
    return { path: p, mimeType: mime, data: buf.toString('base64') }
  })
}

async function generateOnce(PROMPT, refPaths, OUT) {
  const refs = loadRefs(refPaths)
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` }
  try {
    let res
    if (MODEL.startsWith('google/')) {
      res = await fetch(`${VERTEX_BASE}/v1/publishers/google/models/${MODEL.split('/')[1]}:generateContent`, {
        method: 'POST', signal: controller.signal, headers,
        body: JSON.stringify({
          contents: [{ role: 'user', parts: [{ text: PROMPT }, ...refs.map((r) => ({ inlineData: { mimeType: r.mimeType, data: r.data } }))] }],
          generationConfig: { responseModalities: ['TEXT', 'IMAGE'] },
        }),
      })
    } else if (MODEL.startsWith('openai/')) {
      if (refs.length) {
        const form = new FormData()
        form.append('model', MODEL)
        form.append('prompt', PROMPT)
        refs.forEach((r, i) => form.append('image[]', new Blob([Buffer.from(r.data, 'base64')], { type: r.mimeType }), `ref${i}.png`))
        res = await fetch(`${BASE_URL}/images/edits`, { method: 'POST', signal: controller.signal, headers: { Authorization: `Bearer ${KEY}` }, body: form })
      } else {
        res = await fetch(`${BASE_URL}/images/generations`, {
          method: 'POST', signal: controller.signal,
          headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: MODEL, prompt: PROMPT, response_format: 'b64_json', n: 1 }),
        })
      }
    } else {
      const instance = refs.length
        ? { prompt: PROMPT, image: { bytesBase64Encoded: refs[0].data, mimeType: refs[0].mimeType } }
        : { prompt: PROMPT }
      res = await fetch(`${VERTEX_BASE}/v1/publishers/${MODEL.split('/')[0]}/models/${MODEL.split('/')[1]}:predict`, {
        method: 'POST', signal: controller.signal, headers,
        body: JSON.stringify({ instances: [instance], parameters: { sampleCount: 1 } }),
      })
    }

    if (!res.ok) {
      console.error(`[gen] HTTP ${res.status}: ${(await res.text()).slice(0, 500)}`)
      return res.status === 402 ? 5 : 2 // 5 = 402 余额/配额耗尽（批量须整批停止）
    }
    const data = await res.json()

    // 提取图片（三种协议统一扫描）
    let b64 = null, mime = 'image/png'
    const scan = (obj) => {
      if (b64 || !obj || typeof obj !== 'object') return
      if (typeof obj === 'string') {
        const m = obj.match(/^data:(image\/[a-z0-9+.-]+);base64,(.+)$/s)
        if (m) { mime = m[1]; b64 = m[2] }
        return
      }
      for (const k of Object.keys(obj)) {
        if ((k === 'b64_json' || k === 'data' || k === 'inlineData') && typeof obj[k] === 'string' && obj[k].length > 1000) { b64 = obj[k]; return }
        if (k === 'inlineData' && obj[k] && obj[k].data) { mime = obj[k].mimeType || mime; b64 = obj[k].data; return }
        scan(obj[k])
      }
    }
    scan(data)
    if (!b64) {
      console.error('[gen] 响应中未找到图片。原始响应（截断）：')
      console.error(JSON.stringify(data).slice(0, 800))
      return 3
    }

    fs.mkdirSync(path.dirname(OUT), { recursive: true })
    fs.writeFileSync(OUT, Buffer.from(b64, 'base64'))
    console.log(`[gen] 已保存: ${OUT} (${mime}, ${Math.round(b64.length * 3 / 4 / 1024)}KB, refs=${refs.length})`)
    if (QC) await qcCheck(OUT, PROMPT)
    return 0
  } catch (e) {
    console.error('[gen]', e.message)
    return 4
  } finally {
    clearTimeout(timer)
  }
}

// 四轴自检（ftl-studio 风格）：identity / wardrobe / setMatch / manifest，取最弱轴为总分。仅供参考，用户确认为准。
async function qcCheck(imagePath, PROMPT) {
  const buf = fs.readFileSync(imagePath)
  const b = buf.toString('base64')
  const mime = path.extname(imagePath).slice(1) === 'png' ? 'image/png' : 'image/jpeg'
  try {
    const res = await fetch(`${VERTEX_BASE}/v1/publishers/google/models/${CHAT_MODEL.split('/').pop()}:generateContent`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` },
      body: JSON.stringify({
        contents: [{ role: 'user', parts: [
          { text: 'You are an art QC judge for a cinematic interactive-film game. Score this single frame 0-100 on four axes and reply ONLY with JSON: {"identity":n,"wardrobe":n,"setMatch":n,"manifest":n,"weakest":"<axis>","note":"<one short sentence>"}\nidentity = rendered character matches the described character profile; wardrobe = costume continuity; setMatch = location/lighting matches a scene plate; manifest = the frame depicts exactly what the prompt asked.' },
          { text: 'PROMPT:\n' + PROMPT },
          { inlineData: { mimeType: mime, data: b } },
        ] }],
        generationConfig: { responseMimeType: 'application/json' },
      }),
    })
    const data = await res.json()
    const txt = data?.choices?.[0]?.message?.content || data?.candidates?.[0]?.content?.parts?.[0]?.text || ''
    const m = txt.match(/\{[\s\S]*\}/)
    if (m) {
      const qc = JSON.parse(m[0])
      const weakest = Math.min(qc.identity, qc.wardrobe, qc.setMatch, qc.manifest)
      console.log(`[gen] QC: identity=${qc.identity} wardrobe=${qc.wardrobe} setMatch=${qc.setMatch} manifest=${qc.manifest} → 最弱轴 ${weakest} (${qc.weakest})。${qc.note || ''}（仅供参考，以用户确认为准）`)
    } else {
      console.log('[gen] QC 未返回结构化结果，跳过。')
    }
  } catch (e) {
    console.log('[gen] QC 失败（忽略）：', e.message)
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ——— 单图模式 ———
async function singleMode() {
  let PROMPT = arg('prompt')
  const promptFile = arg('prompt-file')
  if (!PROMPT && promptFile) PROMPT = fs.readFileSync(promptFile, 'utf8')
  const OUT = arg('out')
  if (!PROMPT || !OUT) {
    console.error('用法: node gen_batch.mjs --prompt "..." [--ref a.png,b.png] --out out.png（批量模式见脚本头部注释）')
    process.exit(1)
  }
  const refs = (arg('ref') || '').split(',').map((s) => s.trim()).filter(Boolean)
  process.exit(await generateOnce(PROMPT, refs, path.resolve(OUT)))
}

// ——— 批量模式 ———
async function batchMode() {
  const MANIFEST = arg('manifest')
  const TASKS = arg('tasks')
  const FORCE = flag('force')
  const INTERVAL = Number(arg('interval-ms', '2000'))
  const LIMIT = Number(arg('limit', '10')) // 默认每批最多 10 张；--limit 0 = 不限量
  const FILTER = arg('filter', '')
  const GROUP = arg('group', '')
  const STATUSES = String(arg('status', 'prompt_confirmed,failed')).split(',').map((s) => s.trim())

  let projectDir
  const tasks = []
  let manifest = null
  let manifestPath = null

  if (MANIFEST) {
    manifestPath = path.resolve(MANIFEST)
    projectDir = path.resolve(path.dirname(manifestPath), '..') // <项目目录>/images/manifest.json → <项目目录>
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
    for (const [group, dict] of [['scenes', manifest.scenes], ['nodes', manifest.nodes]]) {
      for (const [id, e] of Object.entries(dict || {})) {
        if (e.reusedFrom) continue // lean 档占位节点，不出图
        if (!e.prompt || !e.path) {
          if (STATUSES.includes(e.status)) console.warn(`[batch] ${group}.${id}: status=${e.status} 但缺 prompt/path 槽位，未入队`)
          continue
        }
        tasks.push({ group, id, prompt: e.prompt, refs: e.refs || [], out: path.resolve(projectDir, e.path), entry: e })
      }
    }
  } else {
    const tasksPath = path.resolve(TASKS)
    projectDir = path.resolve(arg('base', path.dirname(tasksPath)))
    for (const t of JSON.parse(fs.readFileSync(tasksPath, 'utf8'))) {
      if (!t.prompt || !t.out) { console.error(`[batch] 任务 ${t.id || '?'} 缺 prompt/out 槽位，已跳过`); continue }
      tasks.push({ group: 'tasks', id: t.id || path.basename(t.out), prompt: t.prompt, refs: t.refs || [], out: path.resolve(projectDir, t.out), entry: t })
    }
  }

  function saveManifest() {
    if (!manifestPath) return
    const tmp = manifestPath + '.tmp'
    fs.writeFileSync(tmp, JSON.stringify(manifest, null, 2))
    fs.renameSync(tmp, manifestPath)
  }

  // 过滤：状态 / 分组 / 关键字 / 已生成跳过 / limit
  const skipped = []
  let queue = []
  for (const t of tasks) {
    const st = t.entry.status
    if (MANIFEST && st && !STATUSES.includes(st)) { skipped.push(`${t.id}(status=${st})`); continue }
    if (GROUP && t.group !== GROUP) { skipped.push(`${t.id}(group)`); continue }
    if (FILTER && !t.id.includes(FILTER)) { skipped.push(`${t.id}(filter)`); continue }
    const exists = fs.existsSync(t.out) && fs.statSync(t.out).size > 0
    if (st === 'rejected') {
      if (exists) { fs.rmSync(t.out); console.log(`[batch] ${t.id}: rejected，已删旧图待重绘`) }
    } else if (exists && !FORCE) {
      skipped.push(`${t.id}(已生成)`)
      if (MANIFEST && st !== 'done') { t.entry.status = 'done'; saveManifest() } // 文件在但账没记 → 补记
      continue
    }
    queue.push(t)
  }
  if (LIMIT > 0 && queue.length > LIMIT) {
    queue.slice(LIMIT).forEach((t) => skipped.push(`${t.id}(limit)`))
    queue = queue.slice(0, LIMIT)
  }

  console.log(`[batch] 待生成 ${queue.length} 张，跳过 ${skipped.length} 张（已生成/状态不符/过滤/limit），间隔 ${INTERVAL}ms，QC=${QC ? 'on' : 'off'}`)

  let ok = 0, fail = 0, consecutiveFails = 0
  for (let i = 0; i < queue.length; i++) {
    const t = queue[i]
    console.log(`\n[batch] (${i + 1}/${queue.length}) ${t.id} → ${path.relative(projectDir, t.out)}`)
    const code = await generateOnce(t.prompt, t.refs.map((r) => path.resolve(projectDir, r)), t.out)
    if (code === 0) {
      ok++; consecutiveFails = 0
      if (MANIFEST) { t.entry.status = 'done'; delete t.entry.error }
      saveManifest()
    } else if (code === 5) {
      // HTTP 402：余额/配额耗尽 —— 整批硬停，不重试不跳过
      fail++
      if (MANIFEST) { t.entry.status = 'failed'; t.entry.error = 'HTTP 402（配额/余额耗尽）' }
      saveManifest()
      console.error(`\n[batch] ⛔ HTTP 402：余额/配额耗尽，整批任务已停止。本轮成功 ${ok} 张，剩余未生成 ${queue.length - i - 1} 张。`)
      console.error('[batch] 请充值或明确指示后重跑同一命令——已生成图片会自动跳过，不会重复消耗配额。')
      process.exit(5)
    } else {
      fail++; consecutiveFails++
      if (MANIFEST) { t.entry.status = 'failed'; t.entry.error = `退出码 ${code}`; t.entry.retries = (t.entry.retries || 0) + 1 }
      saveManifest()
      if (consecutiveFails >= 3) {
        console.error(`[batch] ⛔ 连续 3 次失败（最近退出码 ${code}），停止以免无效消耗。排查后重跑同一命令即可续跑。`)
        process.exit(6)
      }
    }
    if (i < queue.length - 1 && INTERVAL > 0) await sleep(INTERVAL)
  }

  console.log(`\n[batch] 完成：成功 ${ok}，失败 ${fail}，跳过 ${skipped.length}`)
  if (skipped.length) console.log('[batch] 跳过明细: ' + skipped.join(', '))
  process.exit(fail > 0 ? 2 : 0)
}

if (arg('prompt') || arg('prompt-file')) await singleMode()
else if (arg('manifest') || arg('tasks')) await batchMode()
else {
  console.error('用法: node gen_batch.mjs --prompt "..." --out x.jpg（单图） | --manifest <项目目录>/images/manifest.json（批量） | --tasks tasks.json（临时清单）')
  process.exit(1)
}
