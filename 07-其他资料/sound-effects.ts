/**
 * Sound Effects 扩展 —— 为 Pi 增加三种提示音:
 *   ① 成功输入问题(短促轻音)
 *   ② 问题完成(上行双音)
 *   ③ 问题失败(下行低沉双音)
 *
 * 事件依据(对照源码 agent-session.js / 扩展文档):
 *   - input         用户提交输入即触发(重试/continue 不会重复触发)
 *   - agent_settled 所有自动重试/压缩/后续消息都结束后触发,此时才是最终态
 *
 * 安装:放到 ~/.pi/agent/extensions/ 或项目 .pi/extensions/,重启或 /reload 生效
 * 开关:/sound 切换提示音开关(默认开)
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";

let enabled = true;

type Note = [freq: number, durationMs: number];

/** Windows:PowerShell console.beep 播放一组音符(异步、不阻塞) */
function playWindows(notes: Note[]) {
  const script = notes.map(([f, ms]) => `[console]::beep(${f},${ms})`).join(";");
  // PowerShell 每次启动约几百 ms,提示音会有轻微延迟,但足够区分
  // 不用 await,fire-and-forget
  execFile("powershell", ["-NoProfile", "-NonInteractive", "-Command", script], () => {});
}

/** macOS:afplay 系统音效 */
function playMac(file: string) {
  execFile("afplay", [file], () => {});
}

/** Linux:终端响铃(最简);装了 paplay 可换系统音 */
function playLinux() {
  process.stdout.write("\x07");
}

function playInput() {
  if (process.platform === "win32") {
    playWindows([[700, 70]]); // 短促轻音
  } else if (process.platform === "darwin") {
    playMac("/System/Library/Sounds/Tink.aiff");
  } else {
    playLinux();
  }
}

function playSuccess() {
  if (process.platform === "win32") {
    playWindows([
      [880, 120], // 叮
      [1318, 180], // ~叮(上行)
    ]);
  } else if (process.platform === "darwin") {
    playMac("/System/Library/Sounds/Glass.aiff");
  } else {
    playLinux();
  }
}

function playFailure() {
  if (process.platform === "win32") {
    playWindows([
      [392, 200], // 嘟
      [262, 300], // ~嘟(下行低沉)
    ]);
  } else if (process.platform === "darwin") {
    playMac("/System/Library/Sounds/Sosumi.aiff");
  } else {
    playLinux();
  }
}

export default function (pi: ExtensionAPI) {
  // /sound 开关命令
  pi.registerCommand("sound", {
    description: "切换提示音开关",
    handler: async (_args, ctx) => {
      enabled = !enabled;
      ctx.ui.notify(enabled ? "提示音已开启" : "提示音已关闭", "info");
      if (enabled) playInput();
    },
  });

  // ① 成功输入问题 → input 事件(用户提交,只触发一次)
  pi.on("input", () => {
    if (!enabled) return;
    playInput();
  });

  // ②③ 完成/失败 → agent_settled(最终态)
  pi.on("agent_settled", (_event, ctx) => {
    if (!enabled) return;
    const entries = ctx.sessionManager.getBranch();
    const lastAssistant = [...entries]
      .reverse()
      .find((e) => e.type === "message" && e.message.role === "assistant");
    const stop = lastAssistant?.message.stopReason;
    if (stop === "error" || stop === "length") {
      playFailure(); // LLM 报错 / 输出被截断 = 失败
    } else if (stop === "aborted") {
      // 用户主动 Escape 中断,不打扰
      return;
    } else {
      playSuccess();
    }
  });
}

