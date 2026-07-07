# 广域网访问指挥台（云服务器纯转发）

目标：嘉宾用公网 URL 打开网页，体验与局域网访问 `http://<Jetson>:8000` 相同；**云服务器不做缓存、压缩、CDN**，只转发 HTTP + WebSocket。

## 架构

```
嘉宾浏览器 ──HTTPS──► 轻量云 VPS (Caddy/Nginx)
                           │
                    frp / SSH 反向隧道
                           │
                           ▼
                    Jetson :8000  (PhotoMate FastAPI)
```

要点：

- Jetson 通常在 NAT 后，**由 Jetson 主动连出去**建隧道（不需要公网 IP）。
- 网页、REST、`/ws/pose` WebSocket 都走同一条转发，需配置 **WebSocket 升级头**。
- 云服务器**不存地图、不跑业务**，带宽 = 用户与 Jetson 之间的流量（经 VPS 过一遍）。

## 方案 A：frp（推荐，稳定）

### 1. 云 VPS 安装 frps

```bash
# 示例：下载 frp 0.61+，解压后
./frps -c frps.toml
```

`frps.toml` 见同目录 `frps.toml.example`。

### 2. Jetson 安装 frpc

```bash
./frpc -c frpc.toml
```

`frpc.toml` 见 `frpc.toml.example`（把 `serverAddr`、token 改成你的 VPS）。

frp 会把 VPS 的 `127.0.0.1:18000` 转到 Jetson 的 `127.0.0.1:8000`。

### 3. VPS 上 Caddy 对外 HTTPS

`Caddyfile.example`：`your.domain.com` → `reverse_proxy 127.0.0.1:18000`。

嘉宾访问：`https://your.domain.com/`（指挥台）、`https://your.domain.com/docs`（文档）。

### 4. Jetson 上照常启动

```bash
./scripts/run_dashboard.sh
```

---

## 方案 B：SSH 反向隧道（零额外软件，临时演示）

在 **Jetson** 上：

```bash
ssh -N -R 18000:127.0.0.1:8000 user@你的VPS公网IP
```

VPS 上 Caddy/Nginx 仍 `reverse_proxy 127.0.0.1:18000`。断线需 autossh 保活。

---

## 「当作局域网访问」是什么意思？

| 项目 | 说明 |
|------|------|
| URL 路径 | 与内网相同：`/`、`/docs`、`/api/map`、`/ws/pose` |
| 前端 | 用相对路径 + 当前 Host，**不用改 PhotoMate 代码** |
| WebSocket | 浏览器连 `wss://你的域名/ws/pose`，由代理转到 Jetson |
| 延迟 | 比局域网高，地图/位姿仍可用，别指望极低延迟遥控 |

即：**逻辑上仍是访问 Jetson 上的那一个服务**，只是流量经 VPS 绕一圈。

---

## 安全提醒（黑客松最低限度）

公网暴露后建议至少：

1. VPS 防火墙只开 22、80、443
2. frp 设 `auth.token`
3. 演示结束关 frpc / 关隧道
4. 勿把真机「停止导航」以外的高危接口长期裸奔；正式产品再加登录

---

## 自检

```bash
# VPS 上（隧道已建）
curl -s http://127.0.0.1:18000/api/health

# 公网
curl -s https://your.domain.com/api/health
```

应返回 `{"ok":true,"mock":...}`。
