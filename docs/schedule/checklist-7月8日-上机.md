# Checklist：7/8（到赛场，第一次 SSH Jetson）

**今天目标：SSH、SDK、装硬件、mock 网页。不建图、不导航。**

---

## 到场第一件事

- [ ] 领机器人 / 确认 Jetson IP、账号密码  
- [ ] 笔记本连赛场 WiFi 或机器人热点  
- [ ] `ssh user@<jetson-ip>` 成功  
- [ ] `uname -m` → 应为 `aarch64`  

## 硬件安装（计划书 M2–M5）

- [ ] 手机夹具装左手腕，螺丝拧紧  
- [ ] Insta360 USB 插 Jetson，确认 `lsusb` 能看到  
- [ ] 灵巧手通电 / 驱动连通性自测  
- [ ] 打印机放机身，确认能连上 Jetson 或伴生设备  
- [ ] 补光灯、外屏（若有）先固定走线  

## 代码上机

- [ ] 仓库到 Jetson（`git clone` 或 U 盘拷贝，**与 minipc 同一份**）  
- [ ] `git submodule update --init --recursive`（若要 GalbotSDK）  
- [ ] `pip install -r requirements.txt`  
- [ ] `source vendor/GalbotSDK/galbot_sdk/linux-aarch64-gcc940/setup.sh`  
- [ ] `python3 -c "from galbot_sdk.g1 import GalbotNavigation; print('ok')"`（机型按实际 g1/s1）  

## 服务探测（只看不跑长流程）

- [ ] `top` 里是否有 `service_livox_capture`  
- [ ] 是否已有 `/var/maps/cur`（往届地图？没有也正常）  
- [ ] `ls /data/galbot/bin/` 确认 `mapping_server`、`localization_server`、`service_navigation_plan` 存在  

## 网页（仍 mock）

- [ ] `config/app.yaml` → **先保持 `mock: true`**  
- [ ] `./scripts/run_dashboard.sh`  
- [ ] 手机开 `http://<jetson-ip>:8000`（指挥台）  
- [ ] 手机开 `http://<jetson-ip>:8000/docs`（**项目介绍页**，嘉宾扫码用的）  
- [ ] 若打不开：查防火墙 `ufw`、是否 `0.0.0.0` 监听  

## 场地侦察（15 分钟）

- [ ] 走一圈拟建图区域，心里有障碍物  
- [ ] 定 **建图起点**（7/9 早上机器人放这里）  
- [ ] 定 2–3 个 **合影区** 大概位置（9 日打点用）  
- [ ] 问主办方：急停、充电、夜间是否锁场地  

## 8 日收工标准

SSH + 硬件装完 + 指挥台与 `/docs` 手机可访问。**可以睡觉，不要熬夜建图。**
