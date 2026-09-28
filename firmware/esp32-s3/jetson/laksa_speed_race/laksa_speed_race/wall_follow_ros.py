"""ROS 2 wrappers for the simulation-only wall follower and Gym mock.

All topics are under ``/sim/laksa``.  This module deliberately does not import
or publish the physical ``laksa_msgs/DriveCommand`` contract.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile

from .wall_follow_core import MotionRequest, RequestFreshnessGate, ScanFrame, WallFollowController
from .wall_follow_maps import campaign_profiles, generate_corridor_map
from .wall_follow_sim import DT_S, SCAN_INTERVAL_STEPS, create_wall_environment


SCAN_TOPIC = "/sim/laksa/scan"
ODOM_TOPIC = "/sim/laksa/odom"
REQUEST_TOPIC = "/sim/laksa/motion_request"
APPLIED_TOPIC = "/sim/laksa/drive_applied"
STATUS_TOPIC = "/sim/laksa/wall_follow_status"
MAP_FRAME = "sim_laksa_map"
BASE_FRAME = "sim_laksa_base_link"
LIDAR_FRAME = "sim_laksa_lidar"


def controller_main() -> None:
    import rclpy
    from ackermann_msgs.msg import AckermannDriveStamped
    from rclpy.node import Node
    from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String

    class ControllerNode(Node):
        def __init__(self) -> None:
            super().__init__("wall_follow_controller_sim_only")
            self.controller = WallFollowController()
            self.last_receive_s: float | None = None
            self.publisher = self.create_publisher(
                AckermannDriveStamped,
                REQUEST_TOPIC,
                QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE),
            )
            self.status = self.create_publisher(String, STATUS_TOPIC, 10)
            self.create_subscription(
                LaserScan,
                SCAN_TOPIC,
                self.on_scan,
                QoSProfile(
                    history=HistoryPolicy.KEEP_LAST,
                    depth=1,
                    reliability=ReliabilityPolicy.BEST_EFFORT,
                ),
            )
            self.create_timer(0.05, self.watchdog)

        def seconds(self) -> float:
            return self.get_clock().now().nanoseconds * 1e-9

        def publish_request(self, request: MotionRequest) -> None:
            message = AckermannDriveStamped()
            message.header.stamp = self.get_clock().now().to_msg()
            message.header.frame_id = BASE_FRAME
            message.drive.speed = float(request.speed_mps)
            message.drive.steering_angle = float(request.steering_angle_rad)
            self.publisher.publish(message)

        def on_scan(self, message: LaserScan) -> None:
            now_s = self.seconds()
            stamp_s = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
            request, diagnostics = self.controller.update(
                ScanFrame(
                    message.ranges,
                    message.angle_min,
                    message.angle_increment,
                    message.range_min,
                    message.range_max,
                    stamp_s,
                    now_s,
                    frame_id=message.header.frame_id,
                ),
                now_s,
            )
            self.last_receive_s = now_s
            self.publish_request(request)
            status = String()
            status.data = json.dumps(
                {
                    "state": diagnostics.state,
                    "reason": request.reason,
                    "wall_distance_m": diagnostics.wall_distance_m,
                    "front_clearance_m": diagnostics.front_clearance_m,
                },
                sort_keys=True,
            )
            self.status.publish(status)

        def watchdog(self) -> None:
            now_s = self.seconds()
            if self.last_receive_s is None or now_s - self.last_receive_s > self.controller.config.max_scan_receive_age_s:
                self.publish_request(MotionRequest(0.0, 0.0, True, "scan_receive_watchdog", now_s, now_s))

    rclpy.init()
    node = ControllerNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
def simulator_main() -> None:
    import numpy as np
    import rclpy
    from ackermann_msgs.msg import AckermannDriveStamped
    from geometry_msgs.msg import TransformStamped
    from nav_msgs.msg import Odometry
    from rclpy.node import Node
    from sensor_msgs.msg import LaserScan
    from tf2_ros import TransformBroadcaster

    class SimulatorNode(Node):
        def __init__(self) -> None:
            super().__init__("wall_follow_gym_mock_sim_only")
            self.declare_parameter("map_profile", "continuous_wall_30in")
            self.declare_parameter("seed", 101)
            profile_name = str(self.get_parameter("map_profile").value)
            profiles = {profile.name: profile for profile in campaign_profiles()}
            if profile_name not in profiles:
                raise ValueError(f"unknown map_profile {profile_name!r}")
            self.profile = profiles[profile_name]
            self.tempdir = tempfile.TemporaryDirectory(prefix="laksa-wall-follow-")
            record = generate_corridor_map(self.profile, Path(self.tempdir.name) / profile_name)
            self.env, self.observation = create_wall_environment(
                Path(str(record["map_stub"])),
                int(self.get_parameter("seed").value),
                (1.0, self.profile.bottom_y_m + 0.254, 0.0),
            )
            self.gate = RequestFreshnessGate()
            self.sim_time_s = 0.0
            self.scan_pub = self.create_publisher(LaserScan, SCAN_TOPIC, 1)
            self.odom_pub = self.create_publisher(Odometry, ODOM_TOPIC, 1)
            self.applied_pub = self.create_publisher(AckermannDriveStamped, APPLIED_TOPIC, 1)
            self.tf = TransformBroadcaster(self)
            self.create_subscription(AckermannDriveStamped, REQUEST_TOPIC, self.on_request, 1)
            self.create_timer(DT_S, self.step)

        def on_request(self, message: AckermannDriveStamped) -> None:
            self.gate.receive(
                MotionRequest(
                    float(message.drive.speed),
                    float(message.drive.steering_angle),
                    message.drive.speed <= 0.0,
                    "ros_request",
                    self.sim_time_s,
                    self.sim_time_s,
                ),
                self.sim_time_s,
            )

        def step(self) -> None:
            applied = self.gate.apply(self.sim_time_s, DT_S)
            self.observation, _, done, truncated, _ = self.env.step(
                np.asarray([[applied.steering_angle_rad, applied.speed_mps]], dtype=np.float32)
            )
            self.sim_time_s += DT_S
            agent = self.observation["agent_0"]
            state = agent["std_state"]
            stamp = self.get_clock().now().to_msg()
            command = AckermannDriveStamped()
            command.header.stamp = stamp
            command.header.frame_id = BASE_FRAME
            command.drive.speed = float(applied.speed_mps)
            command.drive.steering_angle = float(applied.steering_angle_rad)
            self.applied_pub.publish(command)
            self.publish_pose(stamp, float(state[0]), float(state[1]), float(state[4]), float(state[3]))
            if round(self.sim_time_s / DT_S) % SCAN_INTERVAL_STEPS == 0:
                self.publish_scan(stamp, agent["scan"])
            if bool(agent["collision"]) or done or truncated:
                self.gate = RequestFreshnessGate()

        def publish_pose(self, stamp, x_m: float, y_m: float, yaw: float, speed: float) -> None:
            qz, qw = math.sin(yaw / 2.0), math.cos(yaw / 2.0)
            odom = Odometry()
            odom.header.stamp = stamp
            odom.header.frame_id = MAP_FRAME
            odom.child_frame_id = BASE_FRAME
            odom.pose.pose.position.x = x_m
            odom.pose.pose.position.y = y_m
            odom.pose.pose.orientation.z = qz
            odom.pose.pose.orientation.w = qw
            odom.twist.twist.linear.x = speed
            self.odom_pub.publish(odom)
            transform = TransformStamped()
            transform.header = odom.header
            transform.child_frame_id = BASE_FRAME
            transform.transform.translation.x = x_m
            transform.transform.translation.y = y_m
            transform.transform.rotation = odom.pose.pose.orientation
            lidar = TransformStamped()
            lidar.header.stamp = stamp
            lidar.header.frame_id = BASE_FRAME
            lidar.child_frame_id = LIDAR_FRAME
            lidar.transform.translation.x = 0.31542
            lidar.transform.rotation.w = 1.0
            self.tf.sendTransform([transform, lidar])

        def publish_scan(self, stamp, ranges) -> None:
            scan = LaserScan()
            scan.header.stamp = stamp
            scan.header.frame_id = LIDAR_FRAME
            scan.angle_min = math.radians(-135.0)
            scan.angle_max = math.radians(135.0)
            scan.angle_increment = math.radians(270.0) / 1079.0
            scan.time_increment = 0.0
            scan.scan_time = 0.05
            scan.range_min = 0.0
            scan.range_max = 30.0
            scan.ranges = [float(value) for value in ranges]
            self.scan_pub.publish(scan)

        def destroy_node(self):
            self.env.close()
            self.tempdir.cleanup()
            return super().destroy_node()

    rclpy.init()
    node = SimulatorNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

# There is intentionally no default main: each ROS executable selects one role.
