# 阶段六：部署与启动（deploy）

> 本阶段由原配图阶段的「部署资源与启动框架」拆出，独立成阶段。前置条件：阶段五配图收尾验收通过（check_delivery.js error=0）。

## 目标
将剧本与配图产物部署到 ifg-runtime 预览并正式上架。完整步骤如下，无需再读框架源码。

## 1. 部署字段
project.json 必须填两个字段：`"cover": "cover.jpg"`；`"assetsBase"` = images 目录的站点绝对路径（中文需 URL 编码，如 `/ifg-story-%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4/images/`；上 CDN 时改为 CDN 前缀）。

## 2. 预览入口（文件夹即故事，无需再复制入口）
运行时自带通用入口 `web/play.html`：把项目文件夹名作为参数传入即可挂载，例如
```
http://<IP>:9123/zds_app/ifg-runtime/web/play.html?story=ifg-story-掌门是我杀的
```
- `play.html` 内部会把 `?story=<文件夹>` 自动 URL 编码成 `/<文件夹编码>/project.json` 作为 `STORY_URL`，并把 `ASSETS_BASE` 设为 `/<文件夹编码>/images/`（project.json 自带 `assetsBase` 时以后者优先）。
- 桌面手机视图：`desktop.html?story=<文件夹>`（会把参数透传给 `play.html`）。
- 省略 `?story=` 时默认加载 `ifg-story-掌门是我杀的`；换故事只改这一个参数，**不要**再为每个故事 sed 复制入口。
- 已删除旧的 `xueyuan.html / desktop-xueyuan.html`（对应已删除的雪满刀头）。

> 旧版做法（每个故事复制一份入口）已废弃：`sed "s|__IFG_CONFIG__.STORY_URL = 'story.json';|...|;" index.html > <名字>.html`。

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
- 手机视图：`http://<IP>:9123/zds_app/ifg-runtime/web/desktop.html?story=ifg-story-%E6%8E%8C%E9%97%A8%E6%98%AF%E6%88%91%E6%9D%80%E7%9A%84`（公网 IP 例 47.108.176.183，内网用 `hostname -I`）
- 全屏视图：同路径下 `play.html?story=ifg-story-%E6%8E%8C%E9%97%A8%E6%98%AF%E6%88%91%E6%9D%80%E7%9A%84`
- 正式上架（微信小游戏）：`src/config.js` 填 `STORY_URL`（CDN 上的 project.json）与 `STORY_VERSION`+1；图片传 CDN 后改 `assetsBase`；`project.config.json` 填 appid；广告位 id 按需（不填自动关闭）。
- 环境备注：本机走 7890 代理时，`gen_batch.mjs` 需 `NODE_OPTIONS="--require scripts/proxy-preload.cjs"`（见脚本与参考）。
