# Roadmap

每个版本只做一件事，且都要有**可跑的验收标准**。这是把"学习计划"翻译成"仓库 commit"的方式：
面试时你说"我在做 v0.3"，对方问"做到哪一步了"，你能直接开文件。

---

## v0.3 — 动态环境与里程计融合（4-6 周）

**为什么先做这个**：仓储场景的失败绝大多数来自"人/叉车突然出现"和"里程计漂移"，
而不是规划器不够聪明。这也是具身智能岗位最常问的两个工程问题。

### 3.1 动态障碍

- [ ] 深度相机点云 → `voxel_layer`（`nav2_costmap_2d`），与 `obstacle_layer` 叠加
- [ ] `nav2_collision_monitor` 加急停区（前向 0.4 m 内出现障碍直接发零速）
- [ ] `bench_goals` 增加 `--pedestrians N`：在通道里注入以 0.8 m/s 横穿的行人模型
- [ ] 验收：100 次目标 + 20 次横穿，碰撞 0 次，重规划次数 P95 ≤ 2，成功率 ≥ 0.9

涉及文件：`warehouse_amr_description/config/nav2_params.yaml`（costmap 段）、
`worlds/warehouse.world`（动态 actor）、`bench_goals.py`（场景参数化）

### 3.2 IMU + EKF

- [ ] `description/imu.xacro`：Gazebo IMU 插件（`libgazebo_ros_imu_sensor.so`）
- [ ] `robot_localization` EKF 节点：输入 `/odom` + `/imu/data`，输出 `/odometry/filtered`
- [ ] AMCL 的 odom 源切到 filtered；`my_controllers.yaml` 关掉 `enable_odom_tf` 避免双 TF
- [ ] 验收：直线 10 m 往返，纯轮式 vs EKF 的终点误差对比表（**这才是可以写进 README 的数字**）

### 3.3 定位误差真值度量

- [ ] `bench_localization.py`：订阅 `/gazebo/model_states` + `/amcl_pose`，报 RMSE / P50 / P95
- [ ] README 增加"定位误差"行，附 n 与采样条件（静态定点 / 动态跟踪分开报）

---

## v0.4 — 多机任务分配（4-5 周）

- [ ] `multi_agent_allocator`：中央拍卖（auction）分配 `Mission` 到 N 台车
- [ ] 每台车一个命名空间（`/amr_1/navigate_to_pose`），复用同一份 `mission_server`
- [ ] 冲突消解：先上 `nav2_collision_monitor` + 简单优先级，再考虑时空预约（MAPF）
- [ ] 验收：3 台车 60 个任务，makespan 比单机串行降低 ≥ 40%，任务丢失 0

这一步是"具身智能 + 系统"的分水岭：它同时考调度算法（分配、冲突）、分布式状态（每机 FSM）、
可观测性（每机指标聚合）。

---

## v0.5 — 自动充电对接（3-4 周）

- [ ] ArUco / 反光板标记 → `/dock_pose`（`ros2_aruco` 或自写检测节点）
- [ ] 对接控制器：最后 0.5 m 用低速 + 力矩/接触反馈，退出 Nav2 交给专用控制器
- [ ] FSM 增加 `DOCKING` / `CHARGING` 状态（迁移表里现在是刻意留空的）
- [ ] 验收：20 次对接，成功率 ≥ 0.9，平均对接时间 ≤ 20 s，误触发 0

---

## v1.0 — 实车与策略接口

- [ ] 自写 `ros2_control` 硬件接口（`SystemInterface`）替换社区包 `diffdrive_arduino`
- [ ] 实车数据：`docs/benchmarks/hardware_*.json`，README 增加硬件表
- [ ] VLA / 策略接口：语言或图像输入 → 子目标序列 → 直接喂 `Mission`

接口设计（现在就能定，因为这决定了 v1.0 是加一个节点还是重写）：

```python
# 策略层只负责产生"子目标"，执行与异常处理全部交给经典栈
@dataclass
class SubgoalPlan:
    instruction: str                 # "把 3 号货架的红箱送到 A 区"
    waypoints: list[tuple[float, float, float]]
    grasp_pose: tuple[float, float, float] | None
    confidence: float
```

`mission_server` 已经有 `Mission` 抽象，`SubgoalPlan` → `Mission` 的适配器不超过 50 行。
这也是目前主流 VLA 落地的形态：**策略出子目标，经典规划器保底执行**。

---

## 不做的事（明确划掉）

- 不做 SLAM 算法自研（slam_toolbox 够用，自研是另一个课题）
- 不做自研控制器（DWB / MPPI 足够，除非上到高速或阿克曼）
- 不做 Gazebo 之外的第二套仿真（Isaac Sim 迁移放在 v2，且只在需要 RL 训练时）
