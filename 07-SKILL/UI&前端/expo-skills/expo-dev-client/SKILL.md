---
name: expo-dev-client
description: Framework（开源）。在本地构建和分发 Expo 开发客户端，或通过 TestFlight 分发以供内部测试。生产环境的 TestFlight 发布和应用商店提交，请使用 eas-app-stores skill。
version: 1.1.0
license: MIT
---

使用 EAS Build 创建开发客户端，用于在真机上测试原生代码变更。用它来创建自定义的 Expo Go 客户端，以测试应用的不同分支。

> **本地免费；云端构建收费。** `expo-dev-client` 本身是开源的，本地构建是免费的。通过 EAS Build/TestFlight 构建或分发会消耗你 EAS 套餐中的构建分钟数，并且设备/TestFlight 分发需要付费的 Apple Developer 账号。参见 https://expo.dev/pricing。

## 重要说明：何时需要开发客户端

**开发客户端是任何正式或生产应用的推荐配置。** Expo Go 是一个用于学习和快速实验的平台，只能使用其内置的原生库；大多数应用都会超出它的能力范围，转而使用开发客户端。完整理由参见 [Expo Go 与开发构建的对比](https://docs.expo.dev/develop/development-builds/introduction/)。

只有在以下情况你才需要开发客户端：

- 本地 Expo 模块（自定义原生代码）
- Apple targets（widgets、app clips、扩展）
- Expo Go 中不包含的第三方原生模块
- Config plugins，或测试远程推送通知和 App/Universal Links

## EAS 配置

确保 `eas.json` 中有 development 配置档：

```json
{
  "cli": {
    "version": ">= 16.0.1",
    "appVersionSource": "remote"
  },
  "build": {
    "production": {
      "autoIncrement": true
    },
    "development": {
      "autoIncrement": true,
      "developmentClient": true
    }
  },
  "submit": {
    "production": {},
    "development": {}
  }
}
```

关键设置：

- `developmentClient: true` - 为开发构建打包 expo-dev-client
- `autoIncrement: true` - 自动递增构建号
- `appVersionSource: "remote"` - 使用 EAS 作为版本号的唯一事实来源

## 为 TestFlight 构建

一条命令构建 iOS 开发客户端并提交到 TestFlight：

```bash
eas build -p ios --profile development --submit
```

这条命令会：

1. 在云端构建开发客户端
2. 自动提交到 App Store Connect
3. 在 TestFlight 中构建就绪时给你发送邮件

收到 TestFlight 邮件后：

1. 在你的设备上从 TestFlight 下载该构建
2. 启动应用，查看 expo-dev-client 界面
3. 连接到本地 Metro bundler 或扫描二维码

## 本地构建

在你的机器上构建开发客户端：

```bash
# iOS (requires Xcode)
eas build -p ios --profile development --local

# Android
eas build -p android --profile development --local
```

本地构建的输出：

- iOS：`.ipa` 文件
- Android：`.apk` 或 `.aab` 文件

## 安装本地构建

将 iOS 构建安装到模拟器：

```bash
# Find the .app in the .tar.gz output
tar -xzf build-*.tar.gz
xcrun simctl install booted ./path/to/App.app
```

将 iOS 构建安装到真机（需要签名）：

```bash
# Use Xcode Devices window or ideviceinstaller
ideviceinstaller -i build.ipa
```

安装 Android 构建：

```bash
adb install build.apk
```

## 为指定平台构建

```bash
# iOS only
eas build -p ios --profile development

# Android only
eas build -p android --profile development

# Both platforms
eas build --profile development
```

## 查看构建状态

```bash
# List recent builds
eas build:list

# View build details
eas build:view
```

## 使用开发客户端

安装完成后，开发客户端提供：

- **开发服务器连接** - 输入你的 Metro bundler URL 或扫描二维码
- **构建信息** - 查看原生构建详情
- **启动器界面** - 在不同开发服务器之间切换

连接到本地开发环境：

```bash
# Start Metro bundler
npx expo start --dev-client

# Scan QR code with dev client or enter URL manually
```

## 故障排查

**构建因签名错误失败：**

```bash
eas credentials
```

**清除构建缓存：**

```bash
eas build -p ios --profile development --clear-cache
```

**检查 EAS CLI 版本：**

```bash
eas --version
eas update
```

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-dev-client" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
