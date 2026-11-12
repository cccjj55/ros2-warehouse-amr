"""Gazebo Classic simulation bringup for the warehouse AMR.

Humble notes (this is what the previous version got wrong):
  * controller_manager spawner executable is ``spawner``, not ``spawner.py``
  * the world must be passed explicitly; the old file never loaded one
  * controllers must be spawned *after* the model exists, so they are wired to
    the OnProcessExit event of spawn_entity instead of racing it at t=0
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_amr_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')
    use_joystick = LaunchConfiguration('use_joystick')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', 'rsp.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_ros2_control': 'true',
        }.items(),
    )

    joystick = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', 'joystick.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(use_joystick),
    )

    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[
            os.path.join(pkg_share, 'config', 'twist_mux.yaml'),
            {'use_sim_time': use_sim_time},
        ],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')],
    )

    gazebo_params_file = os.path.join(pkg_share, 'config', 'gazebo_params.yaml')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world,
            'gui': gui,
            'extra_gazebo_args': '--ros-args --params-file ' + gazebo_params_file,
        }.items(),
    )

    spawn_entity_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        # Spawn inside the free aisle at the map origin, not in the wall corner:
        # AMCL seeds from this pose, so it must be collision free.
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'warehouse_amr',
            '-x', '0.9', '-y', '0.6', '-z', '0.05',
        ],
        output='screen',
    )

    spawn_entity = TimerAction(period=3.0, actions=[spawn_entity_node])

    joint_broad_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_broad'],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont'],
        parameters=[{'use_sim_time': use_sim_time}],
        output='screen',
    )

    load_controllers = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_entity_node,
            on_exit=[joint_broad_spawner, diff_drive_spawner],
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true', description='Use the Gazebo clock'),
        DeclareLaunchArgument(
            'world',
            default_value=os.path.join(pkg_share, 'worlds', 'warehouse.world'),
            description='Gazebo world file'),
        DeclareLaunchArgument(
            'gui', default_value='true', description='Start the Gazebo GUI'),
        DeclareLaunchArgument(
            'use_joystick', default_value='false', description='Start teleop joystick chain'),
        rsp,
        joystick,
        twist_mux,
        gazebo,
        spawn_entity,
        load_controllers,
    ])
