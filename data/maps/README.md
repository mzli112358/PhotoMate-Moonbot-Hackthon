# 地图数据目录

## 优先级（`config/app.yaml` → `map`）

1. **`global_cloud.pcd`** — 3D 点云（MID-360 / Galbot 建图等），服务端投影为 2D 俯视图供网页显示
2. **`floor_plan.png`** — 手工俯视 PNG（无 PCD 时使用）
3. 内置演示栅格（以上都没有时）

## Galbot 真机地图

机载建图保存路径示例：`/var/maps/room1102/global_cloud_cleaned.pcd`

可复制到本项目：

```bash
cp /var/maps/cur/global_cloud_cleaned.pcd data/maps/global_cloud.pcd
```

## 其他机器人 MID-360 点云

可放入 `data/maps/global_cloud.pcd` 用于 **Dashboard 可视化**。

注意：与 Galbot 定位用的地图**坐标系、密度、字段可能不同**，不能直接替代 `/var/maps/cur` 给 `localization_server` 用，除非在同一环境用 Galbot 重新建图。

## 网页如何显示

后端读取 PCD → 按高度切片（默认 z: 0.05–2.5 m）→ 栅格化 → `/api/map` 返回 2D 图 + 边界元数据 → 前端 Canvas 绘制底图与机器人位姿。

替换 PCD 后调用 `POST /api/map/reload` 或重启服务。
