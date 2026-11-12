# Benchmark 口径与复现

> 原则：**README 里的每个数字，都必须能由本仓库的脚本重新跑出来。**
> 跑不出来的数字，写进 README 就是给面试官递刀。

## 三档度量

| 档位 | 内容 | 命令 | 是否需要 Gazebo | 耗时 |
| --- | --- | --- | --- | --- |
| L1 单元测试 | 状态机迁移、重试预算、超时、指标聚合 | `make unit` | 否 | ~0.2 s |
| L2 仿真基准 | 随机目标端到端导航成功率 / 耗时 | `make bench` | 是 | ~5-15 min |
| L3 硬件基准 | 同 L2，但真实底盘 + 真实 LiDAR | 手动 | 否 | 取决场地 |

CI 只跑 L1（稳定、零依赖）。L2 需要 Gazebo，放在 `workflow_dispatch` 里按需跑。

## L2：怎么跑

```bash
# 终端 1：无 GUI 全栈
ros2 launch warehouse_amr_description bringup_sim.launch.py gui:=false rviz:=false

# 终端 2：25 个随机目标
ros2 run warehouse_amr_mission bench_goals --ros-args \
    -p n_goals:=25 \
    -p seed:=7 \
    -p goal_timeout_s:=60.0 \
    -p out_json:=docs/benchmarks/latest.json

# 终端 3：把结果刷进 README
python3 scripts/render_bench_table.py docs/benchmarks/latest.json
```

`bench_goals` 的退出码：成功率 ≥ `success_threshold`（默认 0.9）为 0，否则 1。想让它当回归门禁就把它接进 CI。

## 采数纪律（面试时会被追问的部分）

1. **报 n**：25 个目标写 25，不要用"若干次"。
2. **报分布不报最好**：给 P50/P95，不给"最快 3.2 s"。
3. **报失败原因**：`nav_failed` / `goal_timeout` / `goal_rejected` 分开统计，混在一起等于掩盖问题。
4. **固定随机种子**：`seed:=7`，别人才能复现同一组目标点。
5. **记录环境**：commit sha、CPU、`/gazebo/performance_metrics` 的 real-time factor。仿真跑不到实时的机器上，耗时数据不可比。
6. **区分仿真与硬件**：表里 `环境 environment` 一列必须写清楚。

## 数据 schema

`docs/benchmarks/latest.json`：

```json
{
  "meta": {"sim": "gazebo classic / nav2 humble", "goals": 25, "git_sha": "…", "timestamp": "…"},
  "summary": {
    "missions": 25, "succeeded": 24, "failed": 1, "success_rate": 0.96,
    "duration_mean_s": 18.4, "duration_p50_s": 17.1, "duration_p95_s": 33.8,
    "nav_goals_mean": 1.0, "retries_total": 2,
    "failure_reasons": {"goal_timeout": 1}
  },
  "rows": [{"mission_id": "goal_000", "outcome": "succeeded", "duration_s": 16.2, "...": "..."}]
}
```

`warehouse_amr_mission/metrics.py` 负责生成与聚合；`scripts/render_bench_table.py` 负责把
`summary` 渲染成 README 里 `<!-- BENCH:START --> … <!-- BENCH:END -->` 之间的表格。

## 扩展度量：定位误差（当前未实现，属于 v0.3）

想要写"定位误差"，必须有真值。仿真里有真值，所以可以做：

```python
# 伪代码：真值来自 /gazebo/model_states，估计值来自 /amcl_pose
self.create_subscription(ModelStates, '/gazebo/model_states', self.on_truth, 10)
self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.on_est, 10)

def on_est(self, msg):
    if self.truth is None:
        return
    dx = msg.pose.pose.position.x - self.truth.position.x
    dy = msg.pose.pose.position.y - self.truth.position.y
    self.errors.append(math.hypot(dx, dy))   # 采样后取 RMSE / P95，而不是取最小值
```

注意事项：
- 真值与估计值时间戳要对齐（同一 `use_sim_time` 时钟，差值 > 1 帧就丢弃）；
- 报 **RMSE + P95**，不报"平均误差"（会被极端值掩盖）；
- 静态定点（机器人不动）测出的误差不能代表动态跟踪误差，两种都要跑。

## 硬件基准（L3）

Jetson 上跑同一套 `bench_goals`，但需要：

- 起点/目标点用同一张地图（用 `slam_launch.py` 建好的图）；
- 场地地面平整度、光照不影响 LiDAR（结构光/ToF 除外）；
- 记录 `ros2 topic hz /scan`、`ros2 topic hz /cmd_vel`，确认没有被串口或 CPU 限频拖慢；
- 断电重启后重跑一次，确认成功率不是靠"运气好那次"。

**没有 L3 数据时，README 就不要出现"已部署 Jetson 验证"这类表述。** 说"仿真验证 + 硬件集成进行中"更安全，也不会在面试里被一击致命。
