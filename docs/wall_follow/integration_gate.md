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

The ROS mock latches collision/done/truncated episodes, ignores subsequent
requests, and stops stepping that Gym instance. Restart the isolated launch
to begin a fresh episode with a fresh controller. The headless campaign
creates a fresh Gym/controller instance for every case. The ROS terminal path
still needs a Humble run, including a forced collision and restart.

## Reproduce

From `firmware/esp32-s3/jetson/laksa_speed_race`, with the pinned Gym checkout
on `PYTHONPATH`:

```bash
python -m unittest discover -s test -p 'test_wall_follow_*.py' -v
python -m laksa_speed_race.wall_follow_replay test/fixtures/synthetic_scan_bag_fixture.json
python -m laksa_speed_race.wall_follow_sim \
  --config config/wall_follow_v1.json \
  --source-sha "$(git rev-parse HEAD)" \
  --output-dir results/wall_follow_10mm
```

On a Docker/ROS 2 Humble host, the still-unverified ROS boundary can be run with:

```bash
docker compose -f docker-compose.c1.yaml up --build --abort-on-container-exit wall-follow
```

On 2026-09-28, the gate was checked again: neither `docker` nor `ros2` exists
on Windows, and the local Ubuntu-22.04 WSL instance has neither executable nor
`/opt/ros/humble/setup.bash`. The launch command above was therefore not run.
ROS scan/request rates, forced-collision terminal latching, prevention of later
motion/steps, and fresh-episode behavior after launch restart all remain
`UNVERIFIED`; no substitute runtime result is claimed. See
[`ros_humble_gate.md`](ros_humble_gate.md).

The current 10 mm campaign was generated with the pinned Gym checkout and all
85 run records were inspected. Previous results under
`results/wall_follow_20hz` remain historical.

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
