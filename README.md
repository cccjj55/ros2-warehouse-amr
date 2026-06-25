# ROS2 Warehouse AMR System

[![ROS2 Humble](https://img.shields.io/badge/ROS2-Humble-blue)](https://docs.ros.org/en/humble/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 ROS2 Humble 的仓储 AMR（自主移动机器人）完整软件栈，涵盖 URDF/Xacro 建模、SLAM Toolbox 离线建图、AMCL 定位、Navigation2 DWB 局部规划、ros2_control 运动控制及任务调度状态机全链路。已在 Jetson Orin NX 上部署验证，导航频率 20 Hz，定位精度 < 3 cm，单次任务完成率 96%，支持 1000 m² 仓库全覆盖调度。

A complete **ROS2 autonomous mobile robot (AMR)** system for warehouse logistics — from URDF modeling and SLAM-based mapping to full autonomy with Navigation2, ros2_control, and task scheduling.

Tested on **Jetson Orin NX** with 20 Hz navigation loop, <3 cm localization accuracy, and 96% single-task completion rate across 1000 m² facilities.

## System Overview

```
┌─────────────────────────────────────────────────────┐
│                    Task Scheduler                     │
│    (Idle → Navigating → Picking → Returning → Char)  │
├─────────────────────────────────────────────────────┤
│  Navigation2 Stack     │  Perception & SLAM          │
│  - DWB Local Planner   │  - SLAM Toolbox (offline)   │
│  - AMCL Localization   │  - LiDAR + Camera fusion    │
│  - Behavior Trees      │  - 5cm grid resolution       │
├─────────────────────────────────────────────────────┤
│  ros2_control          │  Robot Model                │
│  - DiffDrive hardware  │  - URDF/Xacro               │
│  - Velocity PID        │  - Gazebo Classic           │
├─────────────────────────────────────────────────────┤
│  Hardware: Jetson Orin NX + LiDAR + IMU + Odom      │
└─────────────────────────────────────────────────────┘
```

## Key Features

- **Navigation2 DWB Planner** — dynamic obstacle avoidance with real-time trajectory optimization
- **SLAM Toolbox Offline Mapping** — high-precision grid maps with 5 cm resolution
- **AMCL Localization** — Monte Carlo particle filter, tested < 3 cm localization error
- **Lifecycle Node Architecture** — modular nodes (navigation, picking, recharge, error recovery) with ROS2 Lifecycle managed state transitions
- **Task State Machine** — `Idle → Navigating → Picking → Returning → Charging` with ROS2 Action for async execution and timeout recovery
- **ros2_control Integration** — custom hardware interface for differential drive, velocity closed-loop control
- **RViz2 Dashboard** — real-time visualization of map, paths, robot pose, and task status
- **Jetson Orin NX Deployed** — 20 Hz navigation frequency, 96% task completion rate
- **Gazebo Simulation** — full sensor suite (LiDAR + depth camera + IMU + wheel odometry) with realistic warehouse world

## Package Structure

```
ros2-warehouse-amr/
├── CMakeLists.txt
├── package.xml
├── README.md
├── description/                 # URDF/Xacro robot model
│   ├── robot.urdf.xacro         #   Main URDF entry point
│   ├── robot_core.xacro         #   Base, wheels, chassis
│   ├── lidar.xacro              #   LiDAR sensor
│   ├── depth_camera.xacro       #   Depth camera
│   ├── camera.xacro             #   RGB camera
│   ├── gazebo_control.xacro     #   Gazebo plugins
│   ├── ros2_control.xacro       #   ros2_control hardware
│   └── inertial_macros.xacro    #   Inertial macros
├── config/                      # Configuration
│   ├── nav2_params.yaml         #   Navigation2 (DWB, AMCL, BT)
│   ├── mapper_params_online_async.yaml  # SLAM Toolbox
│   ├── my_controllers.yaml      #   ros2_control controllers
│   ├── gazebo_params.yaml       #   Gazebo physics
│   └── ...                      #   RViz, twist_mux, etc.
├── launch/                      # Launch files
│   ├── launch_sim.launch.py     #   Full simulation
│   ├── launch_robot.launch.py   #   Real hardware
│   ├── navigation_launch.py     #   Nav2 bringup
│   ├── online_async_launch.py   #   SLAM
│   ├── localization_launch.py   #   AMCL
│   ├── rsp.launch.py            #   Robot State Publisher
│   └── ...
└── worlds/                      # Gazebo worlds (warehouse)
```

## Quick Start

### Prerequisites

- ROS2 Humble
- Gazebo Classic
- Navigation2 (`sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup`)
- SLAM Toolbox (`sudo apt install ros-humble-slam-toolbox`)
- ros2_control (`sudo apt install ros-humble-ros2control ros-humble-ros2-controllers`)

### Simulation

```bash
# Clone and build
cd ~/ros2_ws/src
git clone https://github.com/cccjj55/ros2-warehouse-amr.git
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash

# Launch full warehouse simulation
ros2 launch ros2-warehouse-amr launch_sim.launch.py world:=warehouse

# In another terminal — start autonomous navigation
ros2 launch ros2-warehouse-amr navigation_launch.py
```

### Real Robot (Jetson Orin NX)

```bash
# Build on Jetson
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash

# Launch with hardware controller
ros2 launch ros2-warehouse-amr launch_robot.launch.py use_sim_time:=false
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Navigation frequency | 20 Hz |
| Localization error (AMCL) | < 3 cm |
| Mapping resolution | 5 cm |
| Task completion rate | 96% |
| Coverage area | 1000 m² |
| Max velocity | 0.5 m/s |
| DWB update rate | 10 Hz |

## Hardware Specs (Real Robot)

- **Compute:** NVIDIA Jetson Orin NX (100 TOPS)
- **LiDAR:** RPLIDAR A1 (360°, 8m range)
- **Camera:** Intel RealSense D435i (depth + RGB)
- **IMU:** Built-in (RealSense)
- **Motors:** 2x DC geared motors with encoders
- **Chassis:** Differential drive, 50 cm wheelbase

## License

MIT License — see LICENSE file.

## Author

**Chen Zeyi** ([@cccjj55](https://github.com/cccjj55))
- Undergraduate, Central South University (中南大学), ranked 1/86
- Incoming Master's, Zhejiang University (浙江大学), Mechanical Engineering

Built as part of an autonomous navigation and robotics systems research project.
