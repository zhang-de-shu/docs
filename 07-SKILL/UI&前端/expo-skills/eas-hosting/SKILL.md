---
name: eas-hosting
description: EAS 服务（付费）。将 Expo 网站和 Expo Router API 路由部署到 EAS Hosting——导出 web bundle，运行 eas deploy 生成生产和 PR 预览 URL，管理环境变量 secret 与自定义域名，并在 Cloudflare Workers 运行时环境中工作。同时涵盖编写 API 路由（+api.ts handler、HTTP 方法、请求处理、CORS）。在部署 Expo web 应用或 API 路由、搭建 EAS Hosting，或配置托管环境与域名时使用。不适用于原生构建或商店发布——那些请使用 eas-app-stores skill。
version: 1.0.0
license: MIT
---

# EAS Hosting

> **EAS 服务——会产生费用。** EAS Hosting 是 Expo Application Services 的一项付费产品，有免费额度限制；生产部署会使用你所购方案中的请求数和带宽配额。详见 https://expo.dev/pricing。编写 API 路由和导出 web bundle 是免费且开源的，你也可以自行托管导出的 server 输出，而不使用 EAS Hosting。

EAS Hosting 将你的 Expo **web 应用和 API 路由**部署到 Expo 托管的边缘环境（Cloudflare Workers）。使用 `npx expo export -p web` 导出 web bundle，再用 `eas deploy` 发布——同一条命令会一并部署随其打包的所有 Expo Router API 路由。本 skill 涵盖部署网站、编写 API 路由以及托管运行时；部署工作流见下文"部署"小节。

## 何时使用 API 路由

在以下场景使用 API 路由：

- **服务端机密信息** —— API 密钥、数据库凭据或绝不能到达客户端的 token
- **数据库操作** —— 不应暴露的直接数据库查询
- **第三方 API 代理** —— 调用外部服务（OpenAI、Stripe 等）时隐藏 API 密钥
- **服务端校验** —— 在写入数据库前校验数据
- **Webhook 端点** —— 接收来自 Stripe 或 GitHub 等服务的回调
- **限流** —— 在服务端层面控制访问
- **重计算** —— 卸载在移动端上会很慢的处理逻辑

## 何时不该使用 API 路由

以下场景避免使用 API 路由：

- **数据本来就是公开的** —— 直接 fetch 公开 API 即可
- **不需要机密信息** —— 静态数据或客户端可安全执行的操作
- **需要实时更新** —— 使用 WebSockets 或 Supabase Realtime 等服务
- **简单 CRUD** —— 考虑 Firebase、Supabase 或 Convex 等托管后端
- **文件上传** —— 使用直传存储（S3 预签名 URL、Cloudflare R2）
- **仅做认证** —— 使用 Clerk、Auth0 或 Firebase Auth

## 文件结构

API 路由位于 `app` 目录中，以 `+api.ts` 为后缀：

```
app/
  api/
    hello+api.ts          → GET /api/hello
    users+api.ts          → /api/users
    users/[id]+api.ts     → /api/users/:id
  (tabs)/
    index.tsx
```

## 基础 API 路由

```ts
// app/api/hello+api.ts
export function GET(request: Request) {
  return Response.json({ message: "Hello from Expo!" });
}
```

## HTTP 方法

为每种 HTTP 方法导出同名函数：

```ts
// app/api/items+api.ts
export function GET(request: Request) {
  return Response.json({ items: [] });
}

export async function POST(request: Request) {
  const body = await request.json();
  return Response.json({ created: body }, { status: 201 });
}

export async function PUT(request: Request) {
  const body = await request.json();
  return Response.json({ updated: body });
}

export async function DELETE(request: Request) {
  return new Response(null, { status: 204 });
}
```

## 动态路由

```ts
// app/api/users/[id]+api.ts
export function GET(request: Request, { id }: { id: string }) {
  return Response.json({ userId: id });
}
```

## 请求处理

### 查询参数

```ts
export function GET(request: Request) {
  const url = new URL(request.url);
  const page = url.searchParams.get("page") ?? "1";
  const limit = url.searchParams.get("limit") ?? "10";

  return Response.json({ page, limit });
}
```

### 请求头

```ts
export function GET(request: Request) {
  const auth = request.headers.get("Authorization");

  if (!auth) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  return Response.json({ authenticated: true });
}
```

### JSON 请求体

```ts
export async function POST(request: Request) {
  const { email, password } = await request.json();

  if (!email || !password) {
    return Response.json({ error: "Missing fields" }, { status: 400 });
  }

  return Response.json({ success: true });
}
```

## 环境变量

服务端机密信息使用 `process.env`：

```ts
// app/api/ai+api.ts
export async function POST(request: Request) {
  const { prompt } = await request.json();

  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4",
      messages: [{ role: "user", content: prompt }],
    }),
  });

  const data = await response.json();
  return Response.json(data);
}
```

设置环境变量：

- **本地**：创建 `.env` 文件（切勿提交）
- **EAS Hosting**：使用 `eas env:create` 或 Expo dashboard

## CORS 请求头

为 web 客户端添加 CORS：

```ts
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

export function OPTIONS() {
  return new Response(null, { headers: corsHeaders });
}

export function GET() {
  return Response.json({ data: "value" }, { headers: corsHeaders });
}
```

## 错误处理

```ts
export async function POST(request: Request) {
  try {
    const body = await request.json();
    // Process...
    return Response.json({ success: true });
  } catch (error) {
    console.error("API error:", error);
    return Response.json({ error: "Internal server error" }, { status: 500 });
  }
}
```

## 本地测试

启动带 API 路由的开发服务器：

```bash
npx expo serve
```

这会在 `http://localhost:8081` 启动一个本地服务器，完整支持 API 路由。

用 curl 测试：

```bash
curl http://localhost:8081/api/hello
curl -X POST http://localhost:8081/api/users -H "Content-Type: application/json" -d '{"name":"Test"}'
```

## 部署到 EAS Hosting

### 前提条件

```bash
npm install -g eas-cli
eas login
```

### 部署

部署会将你的 web bundle 和所有 Expo Router API 路由一并发布——`eas deploy` 两者都会处理。无论你有完整的网站、仅有 API 路由的后端，还是两者都有，都会执行导出。

```bash
# Export the web bundle (includes any API routes)
npx expo export -p web

# Deploy a preview (PR-style URL)
npx eas-cli@latest deploy

# Deploy to production
npx eas-cli@latest deploy --prod
```

所有内容都会落在 EAS Hosting（Cloudflare Workers）上。

### 生产环境变量

```bash
# Create a secret
eas env:create --name OPENAI_API_KEY --value sk-xxx --environment production

# Or use the Expo dashboard
```

### 自定义域名

在 `eas.json` 或 Expo dashboard 中配置。

### 使用 EAS Workflows 自动化

用 `type: deploy` 的 workflow 在每次 push 到 main 时部署网站（和 API 路由）：

`.eas/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches:
      - main

# https://docs.expo.dev/eas/workflows/syntax/#deploy
jobs:
  deploy_web:
    type: deploy
    params:
      prod: true
```

Pull request 的预览部署使用相同的 job 类型，但设置 `prod: false`：

```yaml
name: Web PR Preview

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  preview:
    type: deploy
    params:
      prod: false
```

若要编写或校验这些示例之外的 workflow YAML，请使用 `eas-workflows` skill。

## EAS Hosting 运行时（Cloudflare Workers）

API 路由运行在 Cloudflare Workers 上。主要限制：

### 缺失/受限的 API

- **没有 Node.js 文件系统** —— `fs` 模块不可用
- **没有 Node 原生模块** —— 使用 Web API 或 polyfill
- **执行时间受限** —— CPU 密集型任务有 30 秒超时
- **没有持久连接** —— WebSockets 需要 Durable Objects
- **fetch 可用** —— 使用标准 fetch 发起 HTTP 请求

### 改用 Web API

```ts
// Use Web Crypto instead of Node crypto
const hash = await crypto.subtle.digest(
  "SHA-256",
  new TextEncoder().encode("data")
);

// Use fetch instead of node-fetch
const response = await fetch("https://api.example.com");

// Use Response/Request (already available)
return new Response(JSON.stringify(data), {
  headers: { "Content-Type": "application/json" },
});
```

### 数据库选项

由于文件系统不可用，请使用云数据库：

- **Cloudflare D1** —— 边缘上的 SQLite
- **Turso** —— 分布式 SQLite
- **PlanetScale** —— Serverless MySQL
- **Supabase** —— 带 REST API 的 Postgres
- **Neon** —— Serverless Postgres

Turso 示例：

```ts
// app/api/users+api.ts
import { createClient } from "@libsql/client/web";

const db = createClient({
  url: process.env.TURSO_URL!,
  authToken: process.env.TURSO_AUTH_TOKEN!,
});

export async function GET() {
  const result = await db.execute("SELECT * FROM users");
  return Response.json(result.rows);
}
```

## 从客户端调用 API 路由

```ts
// From React Native components
const response = await fetch("/api/hello");
const data = await response.json();

// With body
const response = await fetch("/api/users", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "John" }),
});
```

## 常见模式

### 认证中间件

```ts
// utils/auth.ts
export async function requireAuth(request: Request) {
  const token = request.headers.get("Authorization")?.replace("Bearer ", "");

  if (!token) {
    throw new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Verify token...
  return { userId: "123" };
}

// app/api/protected+api.ts
import { requireAuth } from "../../utils/auth";

export async function GET(request: Request) {
  const { userId } = await requireAuth(request);
  return Response.json({ userId });
}
```

### 代理外部 API

```ts
// app/api/weather+api.ts
export async function GET(request: Request) {
  const url = new URL(request.url);
  const city = url.searchParams.get("city");

  const response = await fetch(
    `https://api.weather.com/v1/current?city=${city}&key=${process.env.WEATHER_API_KEY}`
  );

  return Response.json(await response.json());
}
```

## 规则

- 绝不在客户端代码中暴露 API 密钥或机密信息
- 始终校验并清理用户输入
- 使用恰当的 HTTP 状态码（200、201、400、401、404、500）
- 使用 try/catch 优雅地处理错误
- 保持 API 路由职责单一——每个端点只负责一项职责
- 使用 TypeScript 保证类型安全
- 在服务端记录错误日志以便调试

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-hosting" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
