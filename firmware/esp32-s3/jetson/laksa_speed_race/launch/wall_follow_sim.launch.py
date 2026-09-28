from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("map_profile", default_value="continuous_wall_30in"),
            DeclareLaunchArgument("seed", default_value="101"),
            Node(
                package="laksa_speed_race",
                executable="wall_follow_gym_mock",
                name="wall_follow_gym_mock_sim_only",
                parameters=[
                    {
                        "map_profile": LaunchConfiguration("map_profile"),
                        "seed": LaunchConfiguration("seed"),
                    }
                ],
                output="screen",
            ),
            Node(
                package="laksa_speed_race",
                executable="wall_follow_controller",
                name="wall_follow_controller_sim_only",
                output="screen",
            ),
        ]
    )
