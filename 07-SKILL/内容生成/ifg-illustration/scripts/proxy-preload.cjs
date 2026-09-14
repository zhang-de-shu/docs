// 让 Node fetch 遵守 HTTP(S)_PROXY 环境变量（undici 默认不读代理）
try { const { setGlobalDispatcher, EnvHttpProxyAgent } = require('undici'); setGlobalDispatcher(new EnvHttpProxyAgent()); } catch (e) {}
