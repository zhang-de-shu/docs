---
name: expo-data-fetching
description: Framework（开源）。在实现或调试任何网络请求、API 调用或数据获取时使用。涵盖 fetch API、React Query、SWR、错误处理、缓存、离线支持，以及 Expo Router 数据加载器（`useLoaderData`）。
version: 1.0.0
license: MIT
---

# Expo Networking

**任何网络相关的工作都必须使用本 skill，包括 API 请求、数据获取、缓存或网络调试。**

## 参考文档

按需查阅以下资源：

```
references/
  expo-router-loaders.md        Route-level data loading with Expo Router loaders (web, SDK 55+)
  offline-and-cancellation.md   NetInfo network status, offline-first React Query, AbortController
```

## 何时使用

在以下情况使用本 skill：

- 实现 API 请求
- 搭建数据获取（React Query、SWR）
- 使用 Expo Router 数据加载器（`useLoaderData`，web SDK 55+）
- 调试网络故障
- 实现缓存策略
- 处理离线场景
- 身份验证/token 管理
- 配置 API URL 和环境变量

## 偏好

- 避免使用 axios，优先使用 expo/fetch

## 常见问题与解决方案

### 1. 基本 Fetch 用法

**简单的 GET 请求**：

```tsx
const fetchUser = async (userId: string) => {
  const response = await fetch(`https://api.example.com/users/${userId}`);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};
```

**带请求体的 POST 请求**：

```tsx
const createUser = async (userData: UserData) => {
  const response = await fetch("https://api.example.com/users", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }

  return response.json();
};
```

---

### 2. React Query (TanStack Query)

**配置**：

```tsx
// app/_layout.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
    },
  },
});

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <Stack />
    </QueryClientProvider>
  );
}
```

**获取数据**：

```tsx
import { useQuery } from "@tanstack/react-query";

function UserProfile({ userId }: { userId: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => fetchUser(userId),
  });

  if (isLoading) return <Loading />;
  if (error) return <Error message={error.message} />;

  return <Profile user={data} />;
}
```

**变更操作（Mutations）**：

```tsx
import { useMutation, useQueryClient } from "@tanstack/react-query";

function CreateUserForm() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const handleSubmit = (data: UserData) => {
    mutation.mutate(data);
  };

  return <Form onSubmit={handleSubmit} isLoading={mutation.isPending} />;
}
```

---

### 3. 错误处理

**全面的错误处理**：

```tsx
class ApiError extends Error {
  constructor(message: string, public status: number, public code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

const fetchWithErrorHandling = async (url: string, options?: RequestInit) => {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(
        error.message || "Request failed",
        response.status,
        error.code
      );
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network error (no internet, timeout, etc.)
    throw new ApiError("Network error", 0, "NETWORK_ERROR");
  }
};
```

**重试逻辑**：

```tsx
const fetchWithRetry = async (
  url: string,
  options?: RequestInit,
  retries = 3
) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fetchWithErrorHandling(url, options);
    } catch (error) {
      if (i === retries - 1) throw error;
      // Exponential backoff
      await new Promise((r) => setTimeout(r, Math.pow(2, i) * 1000));
    }
  }
};
```

---

### 4. 身份验证

**Token 管理**：

```tsx
import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "auth_token";

export const auth = {
  getToken: () => SecureStore.getItemAsync(TOKEN_KEY),
  setToken: (token: string) => SecureStore.setItemAsync(TOKEN_KEY, token),
  removeToken: () => SecureStore.deleteItemAsync(TOKEN_KEY),
};

// Authenticated fetch wrapper
const authFetch = async (url: string, options: RequestInit = {}) => {
  const token = await auth.getToken();

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: token ? `Bearer ${token}` : "",
    },
  });
};
```

**Token 刷新**：

```tsx
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

const getValidToken = async (): Promise<string> => {
  const token = await auth.getToken();

  if (!token || isTokenExpired(token)) {
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = refreshToken().finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }
    return refreshPromise!;
  }

  return token;
};
```

---

### 5. 离线支持

使用 NetInfo 检测网络状态以及离线优先的 React Query 配置：参见 [./references/offline-and-cancellation.md](./references/offline-and-cancellation.md)。

---

### 6. 环境变量

**使用环境变量配置 API**：

Expo 支持带 `EXPO_PUBLIC_` 前缀的环境变量。这些变量会在构建时内联，并可在你的 JavaScript 代码中使用。

```tsx
// .env
EXPO_PUBLIC_API_URL=https://api.example.com
EXPO_PUBLIC_API_VERSION=v1

// Usage in code
const API_URL = process.env.EXPO_PUBLIC_API_URL;

const fetchUsers = async () => {
  const response = await fetch(`${API_URL}/users`);
  return response.json();
};
```

**按环境区分的配置**：

```tsx
// .env.development
EXPO_PUBLIC_API_URL=http://localhost:3000

// .env.production
EXPO_PUBLIC_API_URL=https://api.production.com
```

**使用环境配置创建 API 客户端**：

```tsx
// api/client.ts
const BASE_URL = process.env.EXPO_PUBLIC_API_URL;

if (!BASE_URL) {
  throw new Error("EXPO_PUBLIC_API_URL is not defined");
}

export const apiClient = {
  get: async <T,>(path: string): Promise<T> => {
    const response = await fetch(`${BASE_URL}${path}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },

  post: async <T,>(path: string, body: unknown): Promise<T> => {
    const response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  },
};
```

**重要说明**：

- 只有带 `EXPO_PUBLIC_` 前缀的变量才会暴露到客户端 bundle 中
- 切勿将机密信息（具有写权限的 API key、数据库密码）放入 `EXPO_PUBLIC_` 变量——它们在构建后的应用中可见
- 环境变量是在**构建时**内联的，而不是运行时
- 修改 `.env` 文件后需要重启 dev server
- 对于 API 路由中的服务端机密信息，请使用不带 `EXPO_PUBLIC_` 前缀的变量

**TypeScript 支持**：

```tsx
// types/env.d.ts
declare global {
  namespace NodeJS {
    interface ProcessEnv {
      EXPO_PUBLIC_API_URL: string;
      EXPO_PUBLIC_API_VERSION?: string;
    }
  }
}

export {};
```

---

### 7. 请求取消

在卸载时使用 AbortController（React Query 会自动取消）：参见 [./references/offline-and-cancellation.md](./references/offline-and-cancellation.md)。

---

## 决策树

```
User asks about networking
  |-- Route-level data loading (web, SDK 55+)?
  |   \-- Expo Router loaders — see references/expo-router-loaders.md
  |
  |-- Basic fetch?
  |   \-- Use fetch API with error handling
  |
  |-- Need caching/state management?
  |   |-- Complex app -> React Query (TanStack Query)
  |   \-- Simpler needs -> SWR or custom hooks
  |
  |-- Authentication?
  |   |-- Token storage -> expo-secure-store
  |   \-- Token refresh -> Implement refresh flow
  |
  |-- Error handling?
  |   |-- Network errors -> Check connectivity first
  |   |-- HTTP errors -> Parse response, throw typed errors
  |   \-- Retries -> Exponential backoff
  |
  |-- Offline support?
  |   |-- Check status -> NetInfo
  |   \-- Queue requests -> React Query persistence
  |
  |-- Environment/API config?
  |   |-- Client-side URLs -> EXPO_PUBLIC_ prefix in .env
  |   |-- Server secrets -> Non-prefixed env vars (API routes only)
  |   \-- Multiple environments -> .env.development, .env.production
  |
  \-- Performance?
      |-- Caching -> React Query with staleTime
      |-- Deduplication -> React Query handles this
      \-- Cancellation -> AbortController or React Query
```

## 常见错误

**错误做法：没有错误处理**

```tsx
const data = await fetch(url).then((r) => r.json());
```

**正确做法：检查响应状态**

```tsx
const response = await fetch(url);
if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();
```

**错误做法：将 token 存储在 AsyncStorage 中**

```tsx
await AsyncStorage.setItem("token", token); // Not secure!
```

**正确做法：对敏感数据使用 SecureStore**

```tsx
await SecureStore.setItemAsync("token", token);
```

## 示例问法

用户："How do I make API calls in React Native?"
-> 使用 fetch，并加上错误处理封装

用户："Should I use React Query or SWR?"
-> 复杂应用用 React Query，较简单的需求用 SWR

用户："My app needs to work offline"
-> 使用 NetInfo 检测网络状态，使用 React Query 持久化进行缓存

用户："How do I handle authentication tokens?"
-> 存储在 expo-secure-store 中，并实现刷新流程

用户："API calls are slow"
-> 检查缓存策略，使用 React Query 的 staleTime
用户："How do I configure different API URLs for dev and prod?"
-> 使用 `EXPO_PUBLIC_` 环境变量，配合 .env.development 和 .env.production 文件
用户："Where should I put my API key?"
-> 客户端可安全使用的 key：放在 .env 中的 `EXPO_PUBLIC_` 变量。机密 key：仅用于 API 路由中的不带前缀的环境变量

用户："How do I load data for a page in Expo Router?"
-> 路由级加载器（web，SDK 55+）参见 references/expo-router-loaders.md。原生端请使用 React Query 或 fetch。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-data-fetching" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
