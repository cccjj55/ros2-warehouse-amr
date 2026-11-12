# Notice / 上游与授权说明

本仓库的 `warehouse_amr_description` 包在结构与部分文件上派生自开源项目
**articubot_one**（作者 Josh Newans，Articulated Robotics / "ROS 2 for Beginners" 课程代码），
该项目以 **MIT License** 发布：

- 上游仓库: https://github.com/joshnewans/articubot_one
- 上游许可: MIT
- 上游版权: Copyright (c) 2022 Josh Newans

## 我们保留的部分（改动极小）

| 文件 / 目录 | 状态 |
| --- | --- |
| `description/*.xacro` | 沿用上游结构，补充 LiDAR / 深度相机 / 仓储底盘尺寸参数 |
| `launch/rsp.launch.py`, `launch/joystick.launch.py`, `launch/camera.launch.py` | 沿用上游，仅替换包名 |
| `config/my_controllers.yaml`, `config/twist_mux.yaml`, `config/joystick.yaml`, `config/gazebo_params.yaml` | 沿用上游，参数按本机底盘调整 |
| `config/main.rviz`, `config/map.rviz` | 沿用上游 RViz 布局 |

## 我们重写或新增的部分（本仓库原创，MIT）

| 文件 / 目录 | 说明 |
| --- | --- |
| `warehouse_amr_description/launch/launch_sim.launch.py` | 重写：Humble 版 controller `spawner`、`world` 参数、延时 spawn 链 |
| `warehouse_amr_description/launch/navigation_launch.py` | 重写：改为包装官方 `nav2_bringup`，替换上游 Foxy 时代的 `nav2_recoveries` 节点列表 |
| `warehouse_amr_description/launch/slam_launch.py` | 新增：slam_toolbox 建图模式 |
| `warehouse_amr_description/launch/bringup_sim.launch.py` | 新增：仿真 + 定位 + Nav2 + RViz 一键栈 |
| `warehouse_amr_description/config/nav2_params.yaml` | 重写：基于 `nav2_bringup` Humble 官方模板重新生成，替换上游 Foxy 参数 |
| `warehouse_amr_description/maps/*` | 新增：示例地图（脚本生成的合成仓库地图，非真实建图产物） |
| `warehouse_amr_description/worlds/warehouse.world` | 新增：货架 + 通道的仓储世界 |
| `warehouse_amr_mission/**` | 全新：任务状态机 / Nav2 Action 调度 / 指标采集 / 随机目标压测 |
| `.github/workflows/ci.yml`, `docker/**`, `scripts/**`, `docs/**` | 新增：CI、容器、基准与文档 |

## 为什么必须写这一节

1. **MIT 的显式要求**：分发衍生代码必须保留原版权声明。原仓库直接把 `LICENSE` 改成
   "Copyright (c) 2025 Chen Zeyi" 且文件被截断（只留下 `Permission is hereby granted...`），
   这在任何一次代码审查里都是硬伤。
2. **面试防御**：技术面试官看到 `ball_tracker`、`my_controllers.yaml` 这类命名会立刻联想到
   课程模板。主动标注"哪些是上游、哪些是我写的"，比被问出来强一百倍。

如果你希望完全摆脱上游，路线是：用 `urdf` 自己重写底盘宏 + 自建 launch + 自建
`nav2_params.yaml`（本仓库已经把后两者做完了，`description/` 是唯一还带着上游痕迹的部分）。
