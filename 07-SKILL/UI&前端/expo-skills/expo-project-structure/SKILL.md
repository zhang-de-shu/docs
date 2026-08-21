---
name: expo-project-structure
description: 框架（OSS）。新建 Expo 应用的目录结构。在使用 Expo Router 搭建或规划新的 Expo 项目、或决定某个文件应放在此类项目的哪个位置时使用。仅适用于新项目——绝不要为了套用本结构而重构已有应用。
version: 1.0.0
license: MIT
---

# Expo 项目结构

一个面向**新建** Expo 应用的起始骨架——即尚未有已提交目录结构的项目。

**仅应用于新项目。** 如果应用已有布局，请遵循其既有约定，让文件留在原处——这是一个可供起步的默认方案，绝不是需要强制推行或向其迁移的标准。当不确定项目是否为新项目时，在移动任何文件之前先询问。

由以下规则汇总而成的完整布局：

```
├── assets/
├── scripts/
├── src/
│   ├── app/                       # Expo Router routes ONLY — every file is a route
│   │   ├── api/                   #   server API routes, grouped here
│   │   │   ├── user+api.ts
│   │   │   └── settings+api.ts
│   │   ├── _layout.tsx
│   │   ├── _layout.web.tsx         #   platform-specific layout
│   │   ├── index.tsx
│   │   └── settings.tsx
│   ├── components/                 # reusable UI: button, card, table…
│   │   ├── table/                  #   complex component → folder + index.tsx
│   │   │   ├── cell.tsx
│   │   │   └── index.tsx
│   │   ├── bar-chart.tsx
│   │   ├── bar-chart.web.tsx        #   platform-specific variant
│   │   └── button.tsx
│   ├── screens/                    # screen bodies that route files render
│   │   ├── home/
│   │   │   ├── card.tsx            #   used only by Home — not shared
│   │   │   └── index.tsx           #   rendered by src/app/index.tsx
│   │   └── settings.tsx
│   ├── server/                     # server-only helpers used by app/api
│   │   ├── auth.ts
│   │   └── db.ts
│   ├── utils/                      # standalone helpers + colocated tests
│   │   ├── format-date.ts
│   │   └── format-date.test.ts
│   ├── hooks/                      # reusable hooks: use-theme.ts…
│   ├── constants.ts
│   └── theme.ts
├── app.json
├── eas.json
└── package.json
```

## `src/` 与 `src/app`

将应用代码放在 `src/` 之下，以将其与配置文件分开。Expo Router 开箱即用地同时支持 `app/` 和 `src/app/`——要切换时，移动目录并重启 bundler 即可。默认模板在 `tsconfig.json` 中将 `@/*` 设为 `./src/*` 的别名。

`src/app` **只放路由**：其中的每个文件都会成为一个路由，因此别的内容都不属于这里。下面要讲的所有内容都放在同级的其他目录中。

## components/ —— 可复用 UI

通用的、被复用的 UI（button、card、table），每个文件使用一个具名导出。文件命名使用 **kebab-case**（`bar-chart.tsx`），与 `create-expo-app` 默认模板保持一致。当组件变大时，为其建立专属目录，以 `index.tsx` 作为入口，并将其私有子组件**就近放置（colocate）**在旁边——导入路径（`@/components/table`）保持不变。

## screens/ —— 界面主体

由于 `app/` 中的文件必须是路由，复杂且不被复用的界面 UI 在那里无处安放。当某个界面大到需要拆分成独立组件时，把它放进 `screens/`，让每个路由只负责渲染其界面：

```tsx
import { Home } from "@/screens/home";

export default function HomeScreen() {
  // route-specific concerns only — e.g. read url params here
  return <Home />;
}
```

将界面的私有组件**就近放置（colocate）**在其目录内（`screens/home/components/`）。还有一个好处：同一个界面可以在多个路由下渲染。

## server/ + app/api/ —— 分离服务端代码

在 `app/` 中的文件名上追加 `+api` 会使其成为服务端 **API 路由**。服务端代码不同于前端代码——它运行在类 Node 的服务端环境中（通过 EAS Hosting 或[第三方服务](https://docs.expo.dev/router/web/api-routes/#hosting-on-third-party-services)部署），并且可以读取机密环境变量（`process.env.X`，而不仅仅是 `EXPO_PUBLIC_*`）。请将其分开存放：

- 将所有路由归组到 `app/api/` 之下 → `/api/user`、`/api/settings`。这样将它们集中放置，并避免冲突（例如 `/user` 界面与 `/user` 路由的冲突）。
- 将共享的纯服务端辅助代码放在 `src/server/` 中。
- 考虑使用 ESLint 规则，将 `+api` 文件和 `server/` 与纯前端的检查规则隔离开来。

## 平台专属代码

小的差异：使用 `Platform.select` / `Platform.OS`。对于较大的差异，拆分为平台文件而不是内联的 `if/else`——`bar-chart.tsx` + `bar-chart.web.tsx`，导入时不带扩展名（`@/components/bar-chart`）；Metro 会针对目标平台选择正确的文件。

- 各平台变体的 props 必须完全相同。
- 始终需要一个默认文件（不带平台扩展名）——如果组件只支持单一平台，可以让默认文件什么都不做（no-op）。
- 支持的扩展名：`.ios`、`.android`、`.native`、`.web`。

## 就近放置样式与测试

- **样式：** 将 `StyleSheet.create({ ... })` 对象放在组件文件底部，而不是单独的 `.styles` 文件中。
- **测试：** 将 `format-date.test.ts` 放在 `format-date.ts` 旁边（优先于单独的 `__tests__/` 目录），这样哪些文件有测试便一目了然。

## AI 与配置文件

代理（agent）指令存放在仓库根目录——`AGENTS.md` / `CLAUDE.md`，项目 skill 放在 `.claude/` 之下。其他配置与资源留在 `src/` 之外：`app.json` / `app.config.ts`、`eas.json`、`package.json`、`assets/` 和 `scripts/`。

---

基于 Kadi Kraman 撰写的 [Expo app folder structure best practices](https://expo.dev/blog/expo-app-folder-structure-best-practices)。关于 `src/` 的优先级与别名机制，请参阅 [Expo 文档](https://docs.expo.dev/router/reference/src-directory/)。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-project-structure" "<actionable feedback>"
```
仅在你有具体且可执行的内容可报告时才提交。请尽可能包含相关上下文。
如果 AI 代理反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval 候选流程，而不是复用上面的命令。
