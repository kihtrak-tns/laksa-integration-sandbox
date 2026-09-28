from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("map_profile", default_value="continuous_wall_30in"),
            DeclareLaunchArgument("seed", default_value="101"),
            DeclareLaunchArgument(
                "collision_test",
                default_value="false",
                description="Simulation-only: start overlapping the map entrance to trigger a Gym collision.",
            ),
            Node(
                package="laksa_speed_race",
                executable="wall_follow_gym_mock",
                name="wall_follow_gym_mock_sim_only",
                parameters=[
                    {
                        "map_profile": LaunchConfiguration("map_profile"),
                        "seed": LaunchConfiguration("seed"),
                        "collision_test": ParameterValue(
                            LaunchConfiguration("collision_test"), value_type=bool
                        ),
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
