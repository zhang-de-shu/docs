---
name: expo-app-clip
description: 框架（开源）。为 Expo 应用添加 iOS App Clip target。当用户提到 App Clip、AASA、apple-app-site-association、appclips、smart app banner，或想在主应用旁边发布一个通过 URL 唤起的轻量级 iOS Clip 时使用。
---

# 为 Expo 应用添加 App Clip

> **要求。** 添加 App Clip target 是开源的。发布它需要 Apple Developer Program 会员资格和 App Store 审核，且 AASA 文件必须通过你域名上的 HTTPS 提供（任何 HTTPS 主机都行；EAS Hosting 是选项之一）。通过 EAS Build 或 `bunx testflight` 构建会使用你 EAS 方案中的构建时长。详见 https://expo.dev/pricing 和 https://developer.apple.com/app-clips/。

为 Expo 项目添加一个 iOS App Clip target。Clip 位于 `targets/clip/`，随主应用一起发布，并通过 Apple App Site Association（AASA）文件从应用域名上的 URL 唤起。

主应用的 bundle ID 变为 `com.<username>.<app-name>`，Clip 的则自动派生为 `<parent>.clip`（例如 `com.bacon.may20.clip`）。

## 1. 设置 `bundleIdentifier` 和 `appleTeamId`

如果缺少这些，`bun create target` 会发出警告。添加到 `app.json`：

```json
{
  "expo": {
    "ios": {
      "bundleIdentifier": "com.<username>.<app-name>",
      "appleTeamId": "XX57RJ5UTD"
    }
  }
}
```

## 2. 添加 App Clip target

```sh
bun create target clip
```

这会安装 [`@bacons/apple-targets`](https://github.com/EvanBacon/expo-apple-targets)，将其添加到 `app.json` 的 `plugins` 数组中，并写入：

- `targets/clip/expo-target.config.js` —— 该 target 的 config plugin
- `targets/clip/Info.plist` —— Clip 的 Info.plist
- `targets/clip/AppDelegate.swift`、`Assets.xcassets` 等

选一个合适的图标，或复用应用中已定义的图标——用 `bunx expo config` 在 `icon` 或 `ios.icon` 键下查看。

## 3. 配置 associated domains

主应用和 Clip 各自都需要指向托管 AASA 文件域名的 Associated Domains entitlement。

在 `app.json` 中，同时添加 `applinks:`（主应用）和 `appclips:`（Clip 唤起）条目：

```json
{
  "expo": {
    "ios": {
      "associatedDomains": [
        "applinks:may20.expo.app",
        "appclips:may20.expo.app"
      ]
    }
  }
}
```

在 `targets/clip/expo-target.config.js` 中，声明 Clip 的 entitlement：

```js
/** @type {import('@bacons/apple-targets/app.plugin').ConfigFunction} */
module.exports = (config) => ({
  type: "clip",
  icon: "https://github.com/expo.png",
  entitlements: {
    "com.apple.developer.associated-domains": ["appclips:may20.expo.app"],
  },
});
```

> 如果你跳过这一步，`expo prebuild` 会打印：`Apple App Clip may require the associated domains entitlement but none were found`。

## 4. 注册 bundle ID 并创建 App Store 条目

```sh
bunx setup-safari
```

这会登录 Apple Developer 账号、注册 `com.bacon.may20`、创建 App Store Connect 条目，并打印：

- 一份起步用的 `apple-app-site-association` JSON
- 一个带 iTunes app id 的 `<meta name="apple-itunes-app">` 标签
- Team ID、iTunes ID 和 Bundle ID

## 5. 托管 AASA 文件

当 iOS 抓取 `https://<your-domain>/.well-known/apple-app-site-association` 并找到匹配的 `appclips` 条目时，App Clip 就被唤起。

```sh
mkdir -p public/.well-known
touch public/.well-known/apple-app-site-association
```

粘贴 `setup-safari` 打印的 JSON，但**为 Clip 的完整 app ID（`<TeamID>.<ClipBundleID>`）添加一个 `appclips` 块**。`setup-safari` 的输出只覆盖主应用：

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["XX57RJ5UTD.com.bacon.may20"],
        "components": [{ "/": "*", "comment": "Matches all routes" }]
      }
    ]
  },
  "appclips": {
    "apps": ["XX57RJ5UTD.com.bacon.may20.clip"]
  },
  "activitycontinuation": {
    "apps": ["XX57RJ5UTD.com.bacon.may20"]
  },
  "webcredentials": {
    "apps": ["XX57RJ5UTD.com.bacon.may20"]
  }
}
```

注意：

- 该文件**没有扩展名**，除了按原样提供之外**没有 `Content-Type` 要求**。Expo Router 静态导出会原样提供 `public/` 中的文件。
- `appclips` 块就是让域名上的 URL 能够启动 Clip 的东西。
- `webcredentials` 用于在网站、主应用和 App Clip 之间共享凭据。
- `activitycontinuation` 是可选的，用于在移动端和桌面端之间共享链接。必须与 expo-router 的 `Head` 一起使用——见 https://docs.expo.dev/router/advanced/apple-handoff/
- 表示法和禁用路由的细节：https://sosumi.ai/documentation/xcode/supporting-associated-domains

## 6. 添加 Smart App Banner meta 标签

创建 `src/app/+html.tsx`（Expo Router 的 HTML 外壳）并添加来自 `setup-safari` 的标签。如果带版本号的模板不存在就创建它：

```sh
bunx expo customize src/app/+html.tsx
```

把 meta 标签添加到 `<head>`：

```tsx
import { ScrollViewStyleReset } from "expo-router/html";

export default function Root({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="apple-itunes-app" content="app-id=6771566491" />
        <ScrollViewStyleReset />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

要让网站显示 App Clip 卡片而不是安装卡片，使用：

```html
<meta
  name="apple-itunes-app"
  content="app-id=6771566491, app-clip-bundle-id=com.bacon.may20.clip, app-clip-display=card"
/>
```

## 7. 部署网站

AASA 文件必须先上线，iOS 才会信任该关联。使用 [EAS Hosting](https://docs.expo.dev/eas/hosting/)：

```sh
bunx expo export -p web
eas deploy --prod
```

这会把网站（包括 `/.well-known/apple-app-site-association`）发布到 `https://<slug>.expo.app`。验证：

```sh
curl https://may20.expo.app/.well-known/apple-app-site-association
```

## 8. 镜像权限

在 prebuild 之后检查主应用的权限：

```sh
npx expo config --type introspect
```

查看 `infoPlist` 对象——在 App Clip 的 `Info.plist` 中镜像这些权限键，以便在 Clip 中可以使用相同的 API。

在 Clip 的 target 配置中设置 `deploymentTarget: "17.6"`——App Clip 在 iOS 17.6 中有更高的最小体积限制。

如果应用使用推送通知或定位服务，添加到 App Clip 的 `Info.plist` 以请求必要的权限：

```xml
<key>NSAppClip</key>
<dict>
  <key>NSAppClipRequestEphemeralUserNotification</key>
  <false/>
  <key>NSAppClipRequestLocationConfirmation</key>
  <true/>
</dict>
```

## 9. 构建并提交到 TestFlight

```sh
bunx testflight
```

这会：

1. 如果缺少 `eas.json` 就生成一个。
2. 为**两个** target（主应用 + Clip）设置凭据。各自有自己的 provisioning profile，但可以共享一个 Distribution Certificate。
3. 同步 capabilities——注意 Clip target 的 `Enabled: Associated Domains`。
4. 构建、上传并安排 TestFlight 提交。

## 10. 配置 App Clip 元数据

把已有的 App Store 元数据拉到本地：

```sh
eas metadata:pull
```

向 `store.config.json` 添加 `apple.appClip`。最多 3 个唤起 URL 可以从网页启动 Clip：

```json
{
  "configVersion": 0,
  "apple": {
    "appClip": {
      "defaultExperience": {
        "action": "PLAY",
        "releaseWithAppStoreVersion": true,
        "reviewDetail": {
          "invocationUrls": ["https://may20.expo.app/", null, null]
        },
        "info": {
          "en-US": {
            "subtitle": "Instantly native with Expo",
            "headerImage": "store/apple/app-clip/en-US/asc-app-clip.png"
          }
        }
      }
    }
  }
}
```

`headerImage` 必须是 1800x1200、不带透明度的 PNG。

推送回商店：

```sh
eas metadata:push
```

Apple 推荐的 App Clip 元数据指南：https://sosumi.ai/documentation/appclip/configuring-the-launch-experience-of-your-app-clip

## 你将得到什么

- 主应用 target：`com.bacon.may20`
- App Clip target：`com.bacon.may20.clip`，位于 `targets/clip/`
- 托管在 `https://may20.expo.app/.well-known/apple-app-site-association` 的 AASA
- 每个 web 路由上的 Smart App Banner meta 标签
- 每个路由都链接到其对应的原生页面
- 嵌入了 Clip 的主应用 TestFlight 构建

一旦 Apple 从域名上的 URL 唤起 Clip，iOS 就会打开 `targets/clip/` 的入口点，加载 React Native 应用。

## 原生检测（可选）

要让 JS 检测它是否运行在 App Clip 中并为完整应用呈现安装提示，创建一个本地 Expo 模块（`bunx create-expo-module --local`）并暴露 `navigator.appClip.prompt()`。

Swift 模块、TypeScript 接口和用法见 [./references/native-module.md](./references/native-module.md)。

## 参考资料

- ./references/native-module.md —— 用于检测 App Clip 环境并呈现 SKOverlay 安装提示的本地 Expo 模块

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-app-clip" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
