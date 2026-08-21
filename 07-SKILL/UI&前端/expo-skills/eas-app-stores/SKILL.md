---
name: eas-app-stores
description: EAS 服务（付费）。使用 EAS 将 Expo 应用部署到应用商店——构建并提交到 iOS App Store、Google Play Store 和 TestFlight，配置 eas.json 的 build 与 submit 配置档，管理应用版本与构建号，以及发布 App Store 元数据和 ASO。当用户想要部署、发布或将应用上线到生产环境或应用商店，正在准备生产构建、运行 eas build 或 eas submit、提交到 TestFlight、提升版本号或构建号，或者设置商店 listing 元数据时使用。若要部署 Expo 网站或 API 路由，请使用 eas-hosting skill。
version: 1.0.0
license: MIT
---

# 应用商店部署

> **EAS 服务——会产生费用。** 本 skill 使用 Expo Application Services（EAS），这是一项有免费额度限制的付费产品。`eas build` 和 `eas submit` 会消耗你所购方案中的构建时长，且提交到商店需要付费的 Apple Developer 和 Google Play 账号。在运行云端命令前，请先查看 https://expo.dev/pricing。

本 skill 涵盖使用 EAS（Expo Application Services）构建并将 Expo 应用发布到 iOS App Store、Google Play Store 和 TestFlight。若要将 Expo 网站或 API 路由部署到 EAS Hosting，请使用 `eas-hosting` skill。

## 参考资料

按需查阅以下资源：

- ./references/workflows.md -- 用于自动化商店发布和 PR 预览的 CI/CD 工作流
- ./references/testflight.md -- 将 iOS 构建提交到 TestFlight 进行 Beta 测试
- ./references/app-store-metadata.md -- 管理 App Store 元数据与 ASO 优化
- ./references/play-store.md -- 将 Android 构建提交到 Google Play Store
- ./references/ios-app-store.md -- iOS App Store 提交与审核流程

## 快速开始

### 安装 EAS CLI

```bash
npm install -g eas-cli
eas login
```

### 初始化 EAS

```bash
npx eas-cli@latest init
```

这会创建带有 build 配置档的 `eas.json`。

## 构建命令

### 生产构建

```bash
# iOS App Store build
npx eas-cli@latest build -p ios --profile production

# Android Play Store build
npx eas-cli@latest build -p android --profile production

# Both platforms
npx eas-cli@latest build --profile production
```

### 提交到商店

```bash
# iOS: Build and submit to App Store Connect
npx eas-cli@latest build -p ios --profile production --submit

# Android: Build and submit to Play Store
npx eas-cli@latest build -p android --profile production --submit

# Shortcut for iOS TestFlight
npx testflight
```

## Web 与 API 路由托管

将 Expo 网站或 Expo Router API 路由部署到 EAS Hosting（先执行 `npx expo export -p web` 再执行 `eas deploy`）由 `eas-hosting` skill 涵盖。本 skill 专注于原生应用商店发布。

## EAS 配置

用于生产部署的标准 `eas.json`：

```json
{
  "cli": {
    "version": ">= 16.0.1",
    "appVersionSource": "remote"
  },
  "build": {
    "production": {
      "autoIncrement": true,
      "ios": {
        "resourceClass": "m-medium"
      }
    },
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    }
  },
  "submit": {
    "production": {
      "ios": {
        "appleId": "your@email.com",
        "ascAppId": "1234567890"
      },
      "android": {
        "serviceAccountKeyPath": "./google-service-account.json",
        "track": "internal"
      }
    }
  }
}
```

## 各平台指南

### iOS

- 使用 `npx testflight` 快速提交到 TestFlight
- 通过 `eas credentials` 配置 Apple 凭据
- 凭据设置见 ./references/testflight.md
- App Store 提交见 ./references/ios-app-store.md

### Android

- 设置 Google Play Console 服务账号
- 配置发布轨道：internal → closed → open → production
- 详细设置见 ./references/play-store.md

## 自动化发布

EAS Workflows 可为 CI/CD 自动化 build → submit → update 流水线。商店发布示例见 ./references/workflows.md。若要编写或校验 workflow YAML，请使用 `eas-workflows` skill——它基于实时 workflow schema 工作。

## 版本管理

使用 `appVersionSource: "remote"` 时，EAS 会自动管理版本号：

```bash
# Check current versions
eas build:version:get

# Manually set version
eas build:version:set -p ios --build-number 42
```

## 监控

```bash
# List recent builds
eas build:list

# Check build status
eas build:view

# View submission status
eas submit:list
```

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-app-stores" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
