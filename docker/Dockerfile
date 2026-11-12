# Reproducible build for the whole stack (ROS 2 Humble + Gazebo Classic).
#
#   docker build -f docker/Dockerfile -t warehouse-amr:humble .
#   docker run --rm -it warehouse-amr:humble bash
#   docker run --rm -it warehouse-amr:humble ros2 launch warehouse_amr_description bringup_sim.launch.py gui:=false rviz:=false
#
# For GUI demo recording run the stack natively (see docs/DEMO.md); the
# container path is for CI, benchmarking and headless checks.
FROM ros:humble-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-colcon-common-extensions \
        python3-pytest \
        ros-humble-navigation2 \
        ros-humble-nav2-bringup \
        ros-humble-slam-toolbox \
        ros-humble-twist-mux \
        ros-humble-ros2-control \
        ros-humble-ros2-controllers \
        ros-humble-gazebo-ros-pkgs \
        ros-humble-xacro \
        ros-humble-teleop-twist-joy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
COPY . /ws/src/ros2-warehouse-amr

RUN bash -c "source /opt/ros/${ROS_DISTRO}/setup.bash && \
             colcon build --symlink-install --event-handlers console_cohesion+"

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
