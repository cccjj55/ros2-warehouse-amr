#!/usr/bin/env bash
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"
if [ -f /ws/install/setup.bash ]; then
    source /ws/install/setup.bash
fi

# Opt-in: start the headless simulation stack before running the command, e.g.
#   DEMO_SIM=1 docker run --rm warehouse-amr:humble \
#       ros2 run warehouse_amr_mission bench_goals --ros-args -p n_goals:=10
if [ "${DEMO_SIM}" = "1" ]; then
    ros2 launch warehouse_amr_description bringup_sim.launch.py \
        gui:=false rviz:=false &
    sleep 25
fi

exec "$@"
