# 阶段六：部署与启动（deploy）

> 本阶段由原配图阶段的「部署资源与启动框架」拆出，独立成阶段。前置条件：阶段五配图收尾验收通过（check_delivery.js error=0）。

## 目标
将剧本与配图产物部署到 ifg-runtime 预览并正式上架。完整步骤如下，无需再读框架源码。

## 1. 部署字段
project.json 必须填两个字段：`"cover": "cover.jpg"`；`"assetsBase"` = images 目录的站点绝对路径（中文需 URL 编码，如 `/ifg-story-%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4/images/`；上 CDN 时改为 CDN 前缀）。

## 2. 预览入口（一次性）
在运行时 `web/` 复制专用入口（不改原 demo）：
```bash
cd /root/zds/zds_app/ifg-runtime/web
sed "s|__IFG_CONFIG__.STORY_URL = 'story.json';|__IFG_CONFIG__.STORY_URL = '/ifg-story-%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4/project.json';" index.html > xueyuan.html
sed 's|src="index.html"|src="xueyuan.html"|' desktop.html > desktop-xueyuan.html
```
⚠️ 已知坑：原版 index.html 漏引 `src/normalize.js`，loader 会永久卡在"正在加载剧情"。先在 `<script src="../src/save.js">` 之前插入 `<script src="../src/normalize.js"></script>`。

## 3. 启动本地服务（端口 9123）
```bash
cat > /tmp/preview_server.py <<'EOF'
import http.server, os, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin','*')
        http.server.SimpleHTTPRequestHandler.end_headers(self)
    def log_message(self,*a): pass
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
os.chdir('/root/zds')   # 服务根 = 项目与运行时的共同父目录
S(('0.0.0.0',9123),H).serve_forever()
EOF
setsid nohup python3 /tmp/preview_server.py >/tmp/preview_server.log 2>&1 < /dev/null & disown
```
- 先查占用：`ss -tln | grep 9123`；9123 历史上跑过旧 http.server，若是僵尸进程直接 kill 接管。注意 9000/9090 等端口已被其他服务占用。
- 中文路径必须 URL 编码（`雪满刀头` → `%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4`）。
- 自检三连（均须 200）：入口 html / `/ifg-story-<项目名URL编码>/project.json` / 任一节点图。

## 4. 访问地址与正式上架
- 手机视图：`http://<IP>:9123/zds_app/ifg-runtime/web/desktop-xueyuan.html`（公网 IP 例 47.108.176.183，内网用 `hostname -I`）
- 全屏视图：同路径下 `xueyuan.html`
- 正式上架（微信小游戏）：`src/config.js` 填 `STORY_URL`（CDN 上的 project.json）与 `STORY_VERSION`+1；图片传 CDN 后改 `assetsBase`；`project.config.json` 填 appid；广告位 id 按需（不填自动关闭）。
- 环境备注：本机走 7890 代理时，`gen_batch.mjs` 需 `NODE_OPTIONS="--require scripts/proxy-preload.cjs"`（见脚本与参考）。
