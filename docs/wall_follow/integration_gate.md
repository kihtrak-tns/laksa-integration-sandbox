# Wall-follow integration note and human-run gate

## Mock contract

The ROS wrapper is isolated under `/sim/laksa/*`:

| Topic | Type | Ownership / QoS intent |
|---|---|---|
| `/sim/laksa/scan` | `sensor_msgs/LaserScan` | Gym mock publishes at 20 Hz; controller subscribes BEST_EFFORT depth 1 |
| `/sim/laksa/odom` | `nav_msgs/Odometry` | Gym truth for inspection/metrics only; never a controller input |
| `/sim/laksa/motion_request` | `ackermann_msgs/AckermannDriveStamped` | controller publishes RELIABLE depth 1 |
| `/sim/laksa/drive_applied` | `ackermann_msgs/AckermannDriveStamped` | independent mock authority reports the bounded command actually applied |
| `/sim/laksa/wall_follow_status` | `std_msgs/String` JSON | diagnostic state only |

Frames are `sim_laksa_map`, `sim_laksa_base_link`, and `sim_laksa_lidar`.
The mock applies a 200 ms request timeout independently of the controller and
continues integrating toward zero after request loss. No physical message type,
topic, device, service, SSH session, or enable path is used.

The evidence runner uses the same 20 Hz scan/request boundary while Gym and
the independent watchdog continue at 100 Hz. A missing scan therefore does not
freeze simulated time or retain a nonzero request indefinitely.

## Reproduce

From `firmware/esp32-s3/jetson/laksa_speed_race`, with the pinned Gym checkout
on `PYTHONPATH`:

```bash
python -m unittest discover -s test -p 'test_wall_follow_*.py' -v
python -m laksa_speed_race.wall_follow_replay test/fixtures/synthetic_scan_bag_fixture.json
python -m laksa_speed_race.wall_follow_sim \
  --config config/wall_follow_v1.json \
  --source-sha "$(git rev-parse HEAD)" \
  --output-dir results/wall_follow_20hz
```

On a Docker/ROS 2 Humble host, the still-unverified ROS boundary can be run with:

```bash
docker compose -f docker-compose.c1.yaml up --build --abort-on-container-exit wall-follow
```

On 2026-09-28, availability checks found no `docker` or `ros2` executable on
Windows and neither executable nor `/opt/ros/humble/setup.bash` in the local
Ubuntu-22.04 WSL instance. The launch command above was therefore not run and
the ROS 2 Humble gate remains `UNVERIFIED`; no substitute runtime result is
claimed.

## Next human-run gate

Do not connect the controller to the car. First, the hardware owner must commit
a real stationary and hand-carried RPLIDAR bag plus TF/driver configuration and
run the controller in read-only replay. Verify frame/yaw, angular ordering,
timestamps, QoS, dropout behavior, doorway/reflective/invalid returns, finite
bounded outputs, and stop requests. Only after that passes should the existing
Orin bring-up plan advance through its battery-unplugged loopback, wheels-up
steering/timeout/brake characterization, wired RJ45 independent stop, and
single-publisher authority review. Low-speed floor testing is a later,
human-observed gate and is not authorized by simulation results.
