"""Real robot bringup (Jetson / x86 + serial wheel driver).

Fixes vs the previous version:
  * ``spawner.py`` -> ``spawner`` (Humble executable name)
  * robot_description is generated with xacro directly instead of the racy
    ``ros2 param get /robot_state_publisher robot_description`` shell-out
  * the hardware plugin is a launch argument, so bench testing on a laptop can
    use ``hardware:=mock`` instead of a serial port that does not exist

The default hardware plugin ``diffdrive_arduino/DiffDriveArduino`` is NOT part
of this repository; install it (or your own ros2_control hardware interface)
before running on real wheels. Simulation does not need it.
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
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_amr_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_joystick = LaunchConfiguration('use_joystick')

    robot_description = ParameterValue(
        Command([
            'xacro ',
            os.path.join(pkg_share, 'description', 'robot.urdf.xacro'),
            ' use_ros2_control:=true',
            ' sim_mode:=false',
        ]),
        value_type=str,
    )

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', 'rsp.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_ros2_control': 'true',
            'sim_mode': 'false',
        }.items(),
    )

    joystick = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', 'joystick.launch.py')),
        condition=IfCondition(use_joystick),
    )

    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[os.path.join(pkg_share, 'config', 'twist_mux.yaml')],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')],
    )

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            {'robot_description': robot_description},
            os.path.join(pkg_share, 'config', 'my_controllers.yaml'),
        ],
        output='screen',
    )

    # On hardware the controller_manager needs a beat for the hardware interface
    # to activate before the spawner services exist.
    delayed_controller_manager = TimerAction(period=3.0, actions=[controller_manager])

    joint_broad_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_broad'],
        output='screen',
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont'],
        output='screen',
    )

    load_controllers = RegisterEventHandler(
        OnProcessStart(
            target_action=controller_manager,
            on_start=[joint_broad_spawner, diff_drive_spawner],
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_joystick', default_value='false'),
        rsp,
        joystick,
        twist_mux,
        delayed_controller_manager,
        load_controllers,
    ])
