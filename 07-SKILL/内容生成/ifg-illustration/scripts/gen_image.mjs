#!/usr/bin/env node
/**
 * 单图生成 CLI（ZenMux OpenAI 兼容网关，参考 LineTale server/index.js imageGeneration）
 *
 * 用法：
 *   node gen_image.mjs --prompt "..." --ref a.png,b.jpg --out images/c1n3.jpg
 *   node gen_image.mjs --prompt-file prompt.txt --ref "a.png, b.png" --out out.png
 *
 * 配置（优先级：命令行 > 环境变量 > 默认）：
 *   --key       ZENMUX_API_KEY
 *   --model     ZENMUX_IMAGE_MODEL（默认 google/gemini-2.5-flash-image）
 *   --base-url  ZENMUX_BASE_URL（默认 https://zenmux.ai/api/v1）
 *
 * 协议自动路由（与 LineTale 一致）：
 *   google/*  → vertex-ai generateContent（responseModalities: TEXT+IMAGE，参考图 inlineData）
 *   openai/*  → /images/generations（无参考图）或 /images/edits（有参考图）
 *   其他       → vertex-ai :predict（参考图仅取首张）
 */
import fs from 'fs'
import path from 'path'

function arg(name) {
  const i = process.argv.indexOf('--' + name)
  return i >= 0 ? process.argv[i + 1] : undefined
}

const KEY = arg('key') || process.env.ZENMUX_API_KEY || ''
const MODEL = arg('model') || process.env.ZENMUX_IMAGE_MODEL || 'google/gemini-2.5-flash-image'
const BASE_URL = (arg('base-url') || process.env.ZENMUX_BASE_URL || 'https://zenmux.ai/api/v1').replace(/\/$/, '')
const VERTEX_BASE = 'https://zenmux.ai/api/vertex-ai'
const OUT = arg('out')
const QC = !!arg('qc')
const CHAT_MODEL = arg('chat-model') || process.env.ZENMUX_CHAT_MODEL || 'google/gemini-2.5-flash'
const TIMEOUT_MS = 180_000

let PROMPT = arg('prompt')
const promptFile = arg('prompt-file')
if (!PROMPT && promptFile) PROMPT = fs.readFileSync(promptFile, 'utf8')
if (!PROMPT || !OUT) {
  console.error('用法: node gen_image.mjs --prompt "..." [--ref a.png,b.png] --out out.png')
  process.exit(1)
}

// 参考图 → {mimeType, data(base64)}
const refs = (arg('ref') || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .map((p) => {
    const buf = fs.readFileSync(p)
    const ext = path.extname(p).slice(1).toLowerCase()
    const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'webp' ? 'image/webp' : ext === 'gif' ? 'image/gif' : 'image/png'
    return { path: p, mimeType: mime, data: buf.toString('base64') }
  })

const controller = new AbortController()
const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` }

async function main() {
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
    console.error(`[gen_image] HTTP ${res.status}: ${(await res.text()).slice(0, 500)}`)
    process.exit(2)
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
    console.error('[gen_image] 响应中未找到图片。原始响应（截断）：')
    console.error(JSON.stringify(data).slice(0, 800))
    process.exit(3)
  }

  fs.mkdirSync(path.dirname(OUT), { recursive: true })
  fs.writeFileSync(OUT, Buffer.from(b64, 'base64'))
  console.log(`[gen_image] 已保存: ${OUT} (${mime}, ${Math.round(b64.length * 3 / 4 / 1024)}KB, refs=${refs.length})`)

  if (QC) await qcCheck(OUT)
}

// 四轴自检（ftl-studio 风格）：identity / wardrobe / setMatch / manifest，取最弱轴为总分。仅供参考。
async function qcCheck(imagePath) {
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
      console.log(`[gen_image] QC: identity=${qc.identity} wardrobe=${qc.wardrobe} setMatch=${qc.setMatch} manifest=${qc.manifest} → 最弱轴 ${weakest} (${qc.weakest})。${qc.note || ''}（仅供参考，以用户确认为准）`)
    } else {
      console.log('[gen_image] QC 未返回结构化结果，跳过。')
    }
  } catch (e) {
    console.log('[gen_image] QC 失败（忽略）：', e.message)
  }
}

main().catch((e) => { console.error('[gen_image]', e.message); process.exit(4) })
