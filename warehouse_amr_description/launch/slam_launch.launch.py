"""SLAM mode: slam_toolbox online async mapping.

Use this to produce the map committed under ``maps/``:

    ros2 launch warehouse_amr_description launch_sim.launch.py
    ros2 launch warehouse_amr_description slam_launch.launch.py
    # drive the robot around the aisles, then:
    ros2 run nav2_map_server map_saver_cli -f ~/warehouse

The map produced this way is the only honest source for the "mapping
resolution" number quoted in the README.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_amr_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    slam_params = LaunchConfiguration('slam_params_file')

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam_params_file': slam_params,
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(pkg_share, 'config', 'mapper_params_online_async.yaml'),
            description='slam_toolbox parameter file'),
        slam,
    ])
