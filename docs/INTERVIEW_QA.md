# 面试问答映射表

**用法**：每个问题右边都指到具体文件。面试时被追问，直接说"在我仓库 `xxx.py` 第 N 段逻辑里"，
比背诵概念强 10 倍。括号里是**不要说的话**。

---

### 1. 这套东西和 `turtlebot3_navigation2` 官方 demo 有什么区别？

官方 demo 是"能走"，本仓库多了任务层与度量层：`warehouse_amr_mission/mission_fsm.py`
（带重试预算与超时的状态机）、`mission_server.py`（Nav2 action 的异步链）、
`bench_goals.py`（随机目标压测）。差别是"能验收"而不是"能演示"。

（不要说"我自己写了整条导航栈"——`nav2_bringup` 是我们 include 的。）

### 2. 为什么用 DWB，不用 MPPI 或 TEB？

DWB 在 Humble 上默认可用、参数少、CPU 友好，配合 20 Hz 控制周期和 0.5 m/s 上限足够；
仓储通道是静态结构化环境，TEB 的连续优化收益不明显，MPPI 在 Jetson 上要多占 GPU/CPU。
切换成本很低：`nav2_params.yaml` 里把 `FollowPath.plugin` 换成
`nav2_mppi_controller::MPPIController` 即可，前提是重新标定 critics。

### 3. costmap 的膨胀半径怎么定？

`robot_radius: 0.25`（底盘 0.335×0.265 的外接圆约 0.21，+4 cm 安全余量）。
膨胀用 `inflation_radius` 与 `cost_scaling_factor` 权衡：通道净宽 2.0 m，两侧货架，
膨胀过大会把通道"掐断"导致规划失败——这是仓储场景最常见的 off-by-one。

### 4. 你的定位精度是多少？怎么测的？

诚实的答案：仿真里 AMCL 在静态定点能到厘米级，但**动态跟踪误差没有在真机上测**，
所以 README 不报具体数字。要测就得有真值：`/gazebo/model_states` 对比 `/amcl_pose`，
报 RMSE + P95（`docs/BENCHMARK.md` 有采集骨架）。

（不要说"< 3 cm"然后拿不出数据——这是最容易翻车的一题。）

### 5. Nav2 为什么需要 lifecycle_manager？

Nav2 节点是有状态的（unconfigured → inactive → active），必须按序 configure/activate：
`map_server` 先加载地图，`amcl` 才能订阅；`planner` 先拿到 costmap，`bt_navigator` 才能规划。
我们直接 include `nav2_bringup`，manager 由它起，`autostart:=true`。

### 6. 状态机为什么不用行为树 / SMACH？

BT 适合"每帧重新决策"的反应式任务；本任务是线性的
`取货 → 放货`，带固定重试预算，用显式迁移表更可读、更好测（24 个单测覆盖所有分支）。
真要做多机+抢占+异常恢复，再上 BT（`nav2_bt_navigator` 已经内建）。

### 7. 重试为什么放在任务层，不交给 Nav2 的 recovery？

Nav2 的 recovery（spin/backup/wait）解决"局部卡住"，不解决"这单配送反正是失败了"。
任务层重试是业务语义：重发 goal、计数、超预算转 `FAILED` 并记录原因。
两层都要有，但责任不同。

### 8. 20 Hz 控制频率意味着什么？

`controller_server` 每 50 ms 出一次速度指令；DWB 的 `sim_time: 1.7` 意味着每次评估
1.7 s 的前向轨迹，采样数 20×5×20。频率降到 5 Hz 时，1.7 s 的仿真窗口内会出现明显
控制滞后，窄通道里表现为画龙。

### 9. 里程计漂移怎么办？

当前是纯轮式里程计（`diff_drive_controller`），没有 IMU 融合——这是已知短板。
补法：`robot_localization` 的 EKF 节点，输入 `/odom` + `/imu/data`（需在 xacro 里加 IMU 插件），
输出 `/odometry/filtered` 给 AMCL 当 `odom` 源。Roadmap v0.3。

### 10. 多机怎么扩展？

任务层已经是"任务 → 航点"的抽象，扩多机的关键是分配器：
`bench_goals` 的单机循环换成中央调度器（拍卖/匈牙利）+ 每机的 goal 抢占；
冲突消解依赖 Nav2 的 `nav2_collision_monitor` 或集中式时空预约（MAPF）。
状态机的 `mission_id` 已经是天然的分片键。

### 11. 动态障碍怎么处理？

现在只有 `obstacle_layer`（LiDAR 打到即标记），慢速行人会"打不到/打到了又消失"。
补法：深度相机点云 → `voxel_layer`，再叠 `nav2_costmap_filters` 的速度限制区。
Roadmap v0.3，验收标准是"人从侧面横穿，重规划 ≤ 1 次且不撞"。

### 12. 你说成功率 96%，统计口径是什么？

`bench_goals` 的口径：一个随机目标从 action 发出到返回 `STATUS_SUCCEEDED` 记为成功；
超时/取消/拒绝都算失败，且分原因统计。n 必须写在表里，P50/P95 一起给。
（"96%"如果是拍脑袋来的，面试官一问 n 就露。）

### 13. Gazebo Classic 要 EOL 了，怎么迁？

`worlds/*.world` 是 SDF，可直接用 `gz sim`；改的是插件（`libgazebo_ros_ray_sensor.so` →
`gz-sim` 的 sensor 系统插件）和 launch 入口（`ros_gz_sim`）。控制层不动，
因为 `ros2_control` 的 `GazeboSystem` 有 `gz_ros2_control` 对应实现。

### 14. ros2_control 的硬件接口怎么写？

继承 `hardware_interface::SystemInterface`，实现 `on_init / on_configure / on_activate /
read / write`：`read()` 里把编码器计数换算成关节位置/速度写进 state interface；
`write()` 里把 velocity command 换算成 PWM/串口帧。当前仓库用的是社区包
`diffdrive_arduino`，不是我自己写的——这点要如实说。

### 15. 踩过最深的坑？

三个真实案例（都在 CHANGELOG 里）：
1. `spawner.py` vs `spawner`：Humble 改可执行名，控制器永远不加载，报错还很不直观；
2. AMCL 初始位姿落在墙里：`(0,0)` 是地图原点不是自由空间，粒子云直接发散；
3. costmap 膨胀把 2 m 通道掐死，规划返回 `NO_VALID_PATH` 但日志只写 "failed"。

### 16. 怎么保证不回归？

L1 单测（0.2 s，24 例，覆盖状态机全分支）+ L2 随机目标压测（成功率门禁）
+ CI 里 `--show-args` 校验所有 launch 能被真实 launch 系统解析。
没有"我本地能跑"这种证据。

### 17. 具身智能方向：这个仓库怎么接 VLA / diffusion policy？

最小可行路径：VLA 输出**离散动作或目标点**，目标点交给 Nav2 执行，形成
"语言/图像 → 子目标 → 经典规划器" 的两级结构（现在主流 VLA 落地都是这个形态）。
仓库里的接入点是 `mission_fsm.py` 的 `Mission` 数据类：把 `pick/drop` 换成
"由策略生成的 waypoint 序列"即可，度量层不用改。

### 18. AI infra 方向：这个项目能讲什么系统侧的东西？

- 可复现：CI 里 `colcon build` + 参数 yaml 解析 + launch 解析，容器镜像固定 Humble；
- 数据管线：`metrics.py` 的 JSONL → 聚合 → README 表格，纯 stdlib、无外部依赖；
- 性能观测：`/gazebo/performance_metrics` 的 real-time factor、`ros2 topic hz` 采样；
- 部署：Jetson 上 `colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release`、
  限频/散热对 20 Hz 控制周期的影响（这是真实瓶颈，不是理论）。

### 19. 如果只能保留一个功能，留哪个？

`bench_goals` + `metrics.py`。因为"能测"才能"能改"；没有度量的机器人项目，
所有优化都是玄学。

### 20. 这个仓库里哪些不是你写的？

`description/*.xacro`、部分 launch（`rsp`/`joystick`/`camera`）、`my_controllers.yaml`、
RViz 布局派生自开源项目 `articubot_one`（Josh Newans，MIT），见 `NOTICE.md`。
我重写的是仿真 launch、Nav2 参数与 bringup、地图/世界、以及整个 `warehouse_amr_mission` 包。

（主动交代上游，是加分项；被问出来才是减分项。）
