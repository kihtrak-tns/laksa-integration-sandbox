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
| `/sim/laksa/gym_status` | `std_msgs/String` JSON | episode ID, Gym step count, terminal reason, and rejected terminal request count |

Frames are `sim_laksa_map`, `sim_laksa_base_link`, and `sim_laksa_lidar`.
The mock applies a 200 ms request timeout independently of the controller and
continues integrating toward zero after request loss. No physical message type,
topic, device, service, SSH session, or enable path is used.

The evidence runner uses the same 20 Hz scan/request boundary while Gym and
the independent watchdog continue at 100 Hz. A missing scan therefore does not
freeze simulated time or retain a nonzero request indefinitely.

The ROS mock latches collision/done/truncated episodes, ignores subsequent
requests, and stops stepping that Gym instance. Its `/sim/laksa/gym_status`
reports an episode ID, Gym step count, terminal reason, and count of rejected
post-terminal requests. The `collision_test:=true` launch option places the
Gym car body into the generated entrance wall as a repeatable simulation-only
collision stimulus. Restart the isolated launch to begin a fresh episode with
a new episode ID and fresh controller. The headless campaign
creates a fresh Gym/controller instance for every case. The ROS terminal path
still needs a Humble run, including a forced collision and restart.

## A6 read-only LaserScan export and replay

Orin Phase A evidence at
[`orin-bringup@2f130607`](../integration/orin_bringup_contract_review.md)
records two multi-gigabyte A6 bags on the Orin. The hand-carried bag is
`~/laksa_evidence/20260928_034706_handcarried` (58.38 s, `/scan` 747 messages,
12.81 Hz); the static bag is
`~/laksa_evidence/20260928_033352_static` (43.44 s, 559 scans, 12.86 Hz).
Neither is a vehicle-drive result. Export only `/scan` on the Orin; the helper
copies serialized CDR bytes and bag timestamps unchanged, writes source bag
identity/hash/counts to `source_identity.json`, and excludes every ZED image
and depth topic:

```bash
python3 /path/to/wall_follow_bag_export.py \
  ~/laksa_evidence/20260928_034706_handcarried \
  ~/laksa_evidence/wall_follow_scan_only_handcarried
ros2 bag info ~/laksa_evidence/wall_follow_scan_only_handcarried
```

The export must contain only `/scan` with type
`sensor_msgs/msg/LaserScan`. Copy that small output directory and its
`source_identity.json` to the simulation host. Keep the source bag on the
Orin. A6 did not record `/tf` or `/tf_static`, so an actual laser-to-base
transform must be supplied and measured separately before interpreting the
controller output as vehicle-frame steering evidence.

On the Humble/Docker simulation host, mount the export read-only and replay at
original bag time. Run the controller with simulated time, remap only into
the simulation namespace, and record request/status messages into a new local
output directory:

```bash
SCAN_BAG=/absolute/path/wall_follow_scan_only_handcarried
OUT="$PWD/results/wall_follow_real_scan_replay_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT"
sudo docker compose -f docker-compose.c1.yaml run --rm --no-deps \
  -v "$SCAN_BAG:/scan_bag:ro" -v "$OUT:/out" wall-follow bash -lc '
    ros2 run laksa_speed_race wall_follow_controller \
      --ros-args -p use_sim_time:=true > /tmp/controller.log 2>&1 &
    controller_pid=$!
    ros2 bag record -o /out/requests /sim/laksa/motion_request \
      /sim/laksa/wall_follow_status &
    recorder_pid=$!
    sleep 2
    ros2 bag play /scan_bag --clock 40 --rate 1.0 \
      --topics /scan --remap "/scan:=/sim/laksa/scan"
    sleep 0.3
    kill -INT "$recorder_pid" 2>/dev/null || true
    kill -INT "$controller_pid" 2>/dev/null || true
    wait "$recorder_pid" || true
    wait "$controller_pid" || true
    cat /tmp/controller.log
  '
```

Audit every recorded request for finite speed/steering within the versioned
simulation bounds. Report controller reasons for invalid scans and stale
headers, and include the 0.18 s receive-age watchdog response to dropped scans.
The committed
`results/wall_follow_10mm/laser_scan_adapter_preflight.json` is a synthetic
preflight only: 12 scans at 12.8 Hz, 1,800 beams, finite bounded requests, an
all-invalid scan stop, and a stale-header stop. It is explicitly not A6 replay.
Until the small export, measured transform, and real output trace are
available, real scan replay stays **UNVERIFIED**.

## ROS terminal-collision observation sequence

The Dell operator has now built and started the isolated Docker service,
measured `/sim/laksa/scan` near 20 Hz, and observed a forced Gym collision at
step 1. The remaining rate, deliberate moving-request, and restart checks
below have not been supplied; see [`ros_humble_gate.md`](ros_humble_gate.md#dell-host-build-live-scan-and-forced-collision-operator-transcript-2026-09-28).
Capture the local checkout SHA and container image ID with the logs. From the
package directory, measure both rates on the **same rebuilt image**:

```bash
git rev-parse HEAD
sudo docker compose -f docker-compose.c1.yaml up --build --force-recreate -d wall-follow
sudo docker inspect --format '{{.Image}}' \
  "$(sudo docker compose -f docker-compose.c1.yaml ps -q wall-follow)"
sudo docker compose -f docker-compose.c1.yaml exec -T wall-follow \
  /usr/local/bin/c1_entrypoint.sh timeout 12 ros2 topic hz /sim/laksa/scan
sudo docker compose -f docker-compose.c1.yaml exec -T wall-follow \
  /usr/local/bin/c1_entrypoint.sh timeout 12 ros2 topic hz /sim/laksa/motion_request
```

For a repeatable collision, run a separate launch with the simulation-only
entrance-wall overlap, then inject later moving requests only on the mock
topic. Save the status immediately after collision and again after the probe;
the Gym step count must be unchanged while the rejected request count rises.
Restart a second launch and verify a different episode ID with a fresh step
counter.

```bash
sudo docker compose -f docker-compose.c1.yaml run -d --no-deps \
  --name wall-follow-collision wall-follow \
  ros2 launch laksa_speed_race wall_follow_sim.launch.py collision_test:=true
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 2 ros2 topic echo --once /sim/laksa/gym_status > collision_before.yaml
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh ros2 topic pub --rate 20 --times 20 \
  /sim/laksa/motion_request ackermann_msgs/msg/AckermannDriveStamped \
  "{drive: {speed: 0.38, steering_angle: 0.2}}"
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 2 ros2 topic echo --once /sim/laksa/gym_status > collision_after.yaml
sudo docker compose -f docker-compose.c1.yaml run -d --no-deps \
  --name wall-follow-restart wall-follow \
  ros2 launch laksa_speed_race wall_follow_sim.launch.py collision_test:=false
sudo docker exec wall-follow-restart /usr/local/bin/c1_entrypoint.sh \
  timeout 2 ros2 topic echo --once /sim/laksa/gym_status > restart_status.yaml
sudo docker logs wall-follow-collision > collision.log 2>&1
sudo docker stop wall-follow-collision wall-follow-restart
```

The `collision_test` launch currently places the initial vehicle pose 0.25 m
before the generated corridor entrance wall. Verify the observed
`gym_collision` reason in the launch logs. The `/sim/laksa/gym_status` 20 Hz
heartbeat makes both the Gym step count and rejected post-terminal request
count observable; its episode ID distinguishes a restarted instance. Because
the controller itself keeps publishing after collision, an increased total
rejection count alone cannot attribute rejections to the deliberate nonzero
probe. Preserve the publisher transcript and before/after status with the
same episode ID and unchanged Gym step count; record this attribution limit.
Keep logs and YAML in the simulation evidence directory. The gate cannot be
marked passed until those results and a fresh restarted episode are recorded.

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
sudo docker compose -f docker-compose.c1.yaml up --build --abort-on-container-exit wall-follow
```

The earlier Windows/WSL runner had neither Docker nor ROS 2 Humble. In the
Dell operator's later isolated launch, ROS scan publication and a forced
collision were observed. The current-image motion-request rate, deliberate
moving-probe freeze, and fresh-episode restart are still pending. See
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
