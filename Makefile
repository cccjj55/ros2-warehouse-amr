SHELL := /bin/bash
ROS_DISTRO ?= humble
BENCH_JSON := docs/benchmarks/latest.json

.DEFAULT_GOAL := help

.PHONY: help build source unit test sim headless mission bench table map lint clean

help: ## 显示可用目标
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

build: ## colcon 构建
	source /opt/ros/$(ROS_DISTRO)/setup.bash && colcon build --symlink-install --event-handlers console_direct+

unit: ## 纯 python 单测（不需要 ROS / Gazebo）
	python3 -m pytest warehouse_amr_mission/test -q

test: ## colcon test（含 lint）
	source /opt/ros/$(ROS_DISTRO)/setup.bash && source install/setup.bash && \
	colcon test --packages-select warehouse_amr_description warehouse_amr_mission && \
	colcon test-result --verbose

sim: ## 仿真 + 定位 + Nav2 + RViz 全栈
	source install/setup.bash && ros2 launch warehouse_amr_description bringup_sim.launch.py

headless: ## 无 GUI 全栈（CI / 远端）
	source install/setup.bash && ros2 launch warehouse_amr_description bringup_sim.launch.py gui:=false rviz:=false

mission: ## 跑 demo 任务集
	source install/setup.bash && ros2 launch warehouse_amr_mission mission.launch.py

bench: ## 25 个随机目标压测，产出 docs/benchmarks/latest.json
	source install/setup.bash && ros2 run warehouse_amr_mission bench_goals --ros-args \
		-p n_goals:=25 -p out_json:=$(BENCH_JSON)

table: ## 用最新 bench 结果刷新 README 表格
	python3 scripts/render_bench_table.py $(BENCH_JSON)

map: ## 重新生成示例地图（合成仓库平面图）
	python3 scripts/make_demo_map.py

docker-build: ## 构建容器镜像
	docker build -f docker/Dockerfile -t warehouse-amr:humble .

clean: ## 清理构建产物
	rm -rf build install log docs/benchmarks/*.jsonl
