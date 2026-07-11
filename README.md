# PhotoMate Moonbot Hackathon

PhotoMate 黑客松总项目仓库。

## 仓库结构

```
PhotoMate-Moonbot-Hackthon/
├── vendor/                 # 平台核心依赖（机器人 / 相机 SDK）
│   ├── GalbotSDK/
│   └── insta360-link2-pro/ # 影石 Insta360 Link 2 Pro SDK（预留）
├── ros/                    # 预留（导航走 Galbot 机载服务，不用 ROS2 SLAM）
├── third_party/            # 其他开源第三方库（预留）
├── models/                 # AI / 重建模型（预留）
├── app/                    # FastAPI 应用（导航 API + WebSocket）
├── webs/                   # Dashboard 静态前端
├── config/                 # app.yaml、waypoints.yaml
├── data/maps/              # 可选 floor_plan.png
├── docs/                   # 项目文档
├── scripts/                # 部署与自动化脚本
├── tools/                  # 开发工具
├── webs/                   # Web 前端 / 可视化
├── manual/                 # 操作手册
├── archive/                # 归档文件
├── reserve/                # 预留目录
├── README.md
└── .gitmodules
```

## 子模块一览

| 目录 | 分类 | 来源 | 分支 | 说明 |
|------|------|------|------|------|
| `vendor/GalbotSDK/` | vendor | [mzli112358/PhotoMate-Moonbot-Hackthon](https://github.com/mzli112358/PhotoMate-Moonbot-Hackthon.git) | `5745f32` | Galbot SDK（历史提交，独立 SDK 布局） |

## 克隆与初始化

```bash
git clone --recurse-submodules https://github.com/mzli112358/PhotoMate-Moonbot-Hackthon.git
cd PhotoMate-Moonbot-Hackthon
```

若已克隆但未拉取子模块：

```bash
git submodule update --init --recursive
```

更新所有子模块到各自跟踪分支的最新提交：

```bash
git submodule update --remote --merge
```

## 快速参考

### Dashboard（Jetson 或开发机）

```bash
# 安装依赖（首次）
pip install -r requirements.txt

# 启动（默认 mock 演示；真机改 config/app.yaml → robot.mock: false）
./scripts/run_dashboard.sh
```

浏览器打开 `http://<本机IP>:8000`（指挥台）或 `http://<本机IP>:8000/docs`（嘉宾文档）。API 调试页在 `/api/swagger`。

### GalbotSDK

```bash
cd vendor/GalbotSDK
source galbot_sdk/linux-x86_64-gcc940/setup.sh
```

导航说明见 [docs/navigate/](./docs/navigate/README.md)（建图 / 定位 / SDK API，不依赖 ROS2）。

Xbox 手柄底盘遥控见 [docs/teleop/](./docs/teleop/README.md)（Galbot G1 @ galbot-echo，无 ROS）。

赛程与全栈执行计划见 [docs/schedule/](./docs/schedule/README.md)（计划书全部模块，7/11 傍晚前搞定）。

