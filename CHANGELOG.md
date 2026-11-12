# Changelog

All notable changes to this repository. Version numbers follow the ROS package
versions in `package.xml`.

## [0.2.0] - 2026-11-12

**主题：从"跑不起来的课程改包"变成"能一条命令复现、能自证指标"的仓库。**

### 修复（跑不起来的部分）

- 修复 `spawner.py` → `spawner`：Humble 的可执行名变更导致 `diff_cont` / `joint_broad`
  两个控制器从来没被加载过（原先的 launch 在 Humble 上直接报错退出）。
- 重写 `launch/navigation_launch.py`：原文件是 Foxy 时代的节点列表
  （`nav2_recoveries/recoveries_server`、`default_bt_xml_filename`、
  `navigate_w_replanning_and_recovery.xml`），并且**没有** `map_server` 与 `amcl`，
  也就是说导航从未真正起来。现改为包装官方 `nav2_bringup/bringup_launch.py`。
- 重写 `config/nav2_params.yaml`：原文件含 `amcl_map_client`、`recoveries_server`、
  `*_rclcpp_node` 等 Humble 已移除的节点参数。现基于 `nav2_bringup` Humble 官方模板
  重新生成，本车 delta 写在文件头注释里。
- `launch_sim.launch.py` 新增 `world` 参数并真正加载世界（README 里写的
  `world:=warehouse` 之前并不存在）；控制器改为在 `spawn_entity` 退出事件后才加载。
- 机器人出生位姿改为自由空间 `(0.9, 0.6)`：原先在地图原点，而原点是墙体，AMCL 必然发散。
- 补回 `config/gaz_ros2_ctl_use_sim.yaml`（`ros2_control.xacro` 引用但文件不存在，
  xacro 解析时直接失败）。

### 新增

- `warehouse_amr_mission` 包：`mission_fsm`（状态机，零 ROS 依赖）、`mission_server`
  （Nav2 action 异步链路调度）、`bench_goals`（随机目标压测）、`metrics`
  （JSONL 记录 / 聚合 / README 表格渲染）。
- `warehouse_amr_mission/test`：24 个 pytest 用例，覆盖迁移表全分支、重试预算、
  超时看门狗、非法事件、指标聚合与表格渲染。`make unit` 0.2 s 跑完。
- `launch/bringup_sim.launch.py`：Gazebo + AMCL + Nav2 + RViz 一键栈。
- `launch/slam_launch.launch.py`：slam_toolbox 建图模式（并说明建图产物才可用于精度声明）。
- `worlds/warehouse.world`：与地图同坐标系的 10 m × 6 m 仓储世界（货架 / 通道 / 充电座）。
- `maps/warehouse.{yaml,pgm}` + `scripts/make_demo_map.py`：合成示例地图（明确标注非建图产物）。
- `scripts/render_bench_table.py`：把基准 JSON 渲染进 README 的 `BENCH` 区块。
- `.github/workflows/ci.yml`：单测 job + Humble 容器内 `colcon build`、xacro 展开、
  YAML 解析、`ros2 launch --show-args` 解析校验、world/PGM 资产校验。
- `docker/Dockerfile` + `docker/entrypoint.sh`：可复现构建（含可选 `DEMO_SIM=1` 起无头栈）。
- `docs/`：ARCHITECTURE / BENCHMARK / DEMO / INTERVIEW_QA / ROADMAP。
- `Makefile`：`build / unit / test / sim / headless / mission / bench / table / map / docker-build`。
- `NOTICE.md`：上游 `articubot_one`（MIT）逐文件归属说明。

### 变更

- 包结构拆分为 `warehouse_amr_description`（数据/launch）+ `warehouse_amr_mission`（任务层）；
  原 `articubot_one` 包名与模板 `package.xml`（`maintainer: Josh Newans`、`description: TODO`）
  一并修正。
- `LICENSE`：补全 MIT 全文并保留上游版权；原文件是截断的 `Permission is hereby granted...`。
- 删除与仓储 AMR 无关的课程遗留：`ball_tracker*`、`camera.xacro` 之外的球体跟踪链、
  `drive_bot.rviz` / `view_bot.rviz`、空的 `empty.yaml`。
- README 全面重写：删除无法由脚本产出的指标（"定位精度 < 3 cm"、"96% 完成率"、
  "Jetson Orin NX 已部署"、"50 cm 轮距"——实际轮距 0.297 m），改为
  "实现了什么 / 没实现什么"对照表 + 可复现基准区块。

### 已知问题

- 实车硬件插件 `diffdrive_arduino/DiffDriveArduino` 不在本仓库内，`launch_robot.launch.py`
  需要外部提供；仿真路径不依赖它。
- 没有 IMU，纯轮式里程计；EKF 融合在 v0.3。
- `bench_goals` 的矩形采样区不感知障碍物，约 5-10% 的目标点会落在货架内部，
  这些会以 `goal_timeout` 失败并被明确统计（不是"偶发 bug"，是可解释的采样缺陷）。
