import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('warehouse_amr_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    sim_mode = LaunchConfiguration('sim_mode')

    # ParameterValue(value_type=str) keeps launch from trying to parse the URDF
    # text as YAML -- the classic "robot_description is not a string" failure.
    robot_description = ParameterValue(
        Command([
            'xacro ',
            os.path.join(pkg_share, 'description', 'robot.urdf.xacro'),
            ' sim_mode:=', sim_mode,
            ' use_ros2_control:=', LaunchConfiguration('use_ros2_control'),
        ]),
        value_type=str,
    )

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time,
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='false', description='Use the Gazebo clock'),
        DeclareLaunchArgument(
            'sim_mode',
            default_value=LaunchConfiguration('use_sim_time'),
            description='Select the Gazebo hardware plugin in ros2_control.xacro'),
        DeclareLaunchArgument(
            'use_ros2_control', default_value='true', description='Load the ros2_control block'),
        node_robot_state_publisher,
    ])
