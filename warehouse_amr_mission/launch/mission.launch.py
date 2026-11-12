"""Start the mission server against a running Nav2 stack.

    ros2 launch warehouse_amr_mission mission.launch.py

Defaults point at the bundled demo missions; override with
``missions_file:=/abs/path/to/missions.yaml``.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_amr_mission')

    missions_file = LaunchConfiguration('missions_file')
    metrics_path = LaunchConfiguration('metrics_path')
    autostart = LaunchConfiguration('autostart')
    loop = LaunchConfiguration('loop')
    use_sim_time = LaunchConfiguration('use_sim_time')

    mission_server = Node(
        package='warehouse_amr_mission',
        executable='mission_server',
        name='mission_server',
        output='screen',
        parameters=[
            os.path.join(pkg_share, 'config', 'mission_params.yaml'),
            {
                'missions_file': missions_file,
                'metrics_path': metrics_path,
                'autostart': ParameterValue(autostart, value_type=bool),
                'loop': ParameterValue(loop, value_type=bool),
                'use_sim_time': ParameterValue(use_sim_time, value_type=bool),
            },
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'missions_file',
            default_value=os.path.join(pkg_share, 'config', 'missions_demo.yaml'),
            description='Mission list yaml'),
        DeclareLaunchArgument(
            'metrics_path', default_value='', description='JSONL output path (empty disables)'),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('loop', default_value='false'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        mission_server,
    ])
