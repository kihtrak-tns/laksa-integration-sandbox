# ROS 2 Humble execution gate

Date: 2026-09-28 UTC. Scope: isolated simulation only.

The initial execution-host inventory was checked without starting any hardware or production
service:

```text
Windows Docker: UNAVAILABLE
Windows ros2: UNAVAILABLE
Ubuntu-22.04 WSL docker: UNAVAILABLE
Ubuntu-22.04 WSL ros2: UNAVAILABLE
Ubuntu-22.04 WSL /opt/ros/humble/setup.bash: UNAVAILABLE
LAN Ubuntu candidate: 192.168.1.236
SSH probe: connection timed out on port 22 after 8 seconds
```

The bounded remote probe was:

```powershell
Resolve-DnsName ubuntu -Type A
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 ubuntu `
  "hostname; command -v ros2; test -f /opt/ros/humble/setup.bash; command -v docker"
```

Name resolution returned `192.168.1.236`; SSH timed out before authentication,
so no command ran on that host and its OS or ROS state is unknown. No password,
key, package installation, physical device, or car connection was attempted.
The source available for the attempted gate was wall-follow head
`6a685098163e8a4abcd7fbb39dea6c640b74f3cd`; the later integration merge is
`92ed803cdb9e331312139b888c6da4ebf195f25f` against base
`f9676915ff71d3e7f22ed588e8054e5ce7cf9c72`.

At that initial checkpoint, `wall_follow_sim.launch.py` had not run. The observations recorded in later sections supersede this initial state; no ROS-observed scan rate,
motion-request rate, collision latch, post-terminal request rejection, blocked
terminal stepping, or fresh episode was then available. Portable
focused tests exercise the terminal authority state machine, but that is not a
substitute for executing the ROS wrapper and pinned Gym together.

Initial gate state: **UNVERIFIED**. The next suitable Docker/ROS 2 Humble host must run
the isolated launch, measure both topic rates, force a Gym collision, verify
that later requests cannot move or step that terminal episode, terminate the
launch, and verify that a fresh launch creates a fresh episode. No physical
command topic or car device is part of this gate.

## Dell Docker attempt (2026-09-28)

At the time of this earlier attempt, the latest `codex/wall-follow-gym` source available was
`ac67271b94e6844f2a420a1d901ec171f13099b9`. The Compose file lists the
`wall-follow` service and `docker compose ... config --services` succeeded.
The Dell reports Docker Engine client version `29.8.1` (API `1.56`), but this
execution session cannot access its daemon socket. `docker info` and the
`wall-follow` image build both failed with:

```text
permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock
```

The socket is presented as `nobody:nogroup` mode `srw-rw----`; the session is
UID 1000 and has `nogroup`, but access is still denied by the runner. `sudo -v`
cannot elevate inside this runner because `no new privileges` is set. The
commands actually attempted were:

```bash
docker version
docker info --format '{{.ServerVersion}}'
docker compose -f firmware/esp32-s3/jetson/laksa_speed_race/docker-compose.c1.yaml config --services
docker compose -f firmware/esp32-s3/jetson/laksa_speed_race/docker-compose.c1.yaml build wall-follow
sudo -v
```

The Compose service was not built or launched in that restricted attempt. No ROS nodes ran in that attempt, so there were
no observed `/sim/laksa/scan` or `/sim/laksa/motion_request` rates, no forced
collision result, no post-collision moving-request observation, and no launch
restart/fresh-episode observation. These checks remain **UNVERIFIED**. No build
fix was needed or attempted; the build did not reach Docker. No hardware or
physical command topic was accessed. No Docker build fix was made during this
attempt because the failure occurred before the daemon accepted the request;
the later source-only Gym build-backend adjustment is recorded below.

## Updated branch retry (2026-09-28)

The branch subsequently added a pinned Gym build-backend fix at
`386c86869ed68cbc9c77b7e44454dfc3173b5881`: install `uv_build==0.9.30` and
use `pip --no-build-isolation` for the pinned Gym checkout. This is a source
fix only; it is not a verified successful image build. On that exact head,
`docker compose ... config --services` still listed `wall-follow`, but the
updated build was retried and failed before Docker could execute a build:

```text
$ docker compose -f firmware/esp32-s3/jetson/laksa_speed_race/docker-compose.c1.yaml build wall-follow
Image laksa_speed_race-wall-follow Building
permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock
```

The same runner cannot resolve the Orin SSH alias `dev-orin`, so the A6 bag
could not be exported here either. A repeatable simulation-only collision
stimulus (`collision_test:=true`) and `/sim/laksa/gym_status` counters are now
implemented on the branch. At that update, the Dell Humble run had not yet been supplied: no measured topic
rates, Gym collision, rejected-request count, frozen step count, or new
episode ID after restart was then available. The later operator evidence is recorded below.

The tested offline replay/collision-probe source is
`d325f12ed721e407d9e2a2b6f23607e3d8fc6585`. The focused command results were:
scan adapter/export/preflight 5/5 PASS, controller core 10/10 PASS, interface
isolation/config 2/2 PASS, and `compileall` PASS. Those local checks cover the
portable path and static interface contracts, not ROS node execution.

## Earlier Dell topic-rate observation (operator terminal, 2026-09-28)

The operator ran the following two commands from the package directory using
`sudo docker compose` and the existing `wall-follow` container:

```bash
sudo docker compose -f docker-compose.c1.yaml exec -T wall-follow \
  /usr/local/bin/c1_entrypoint.sh timeout 8 ros2 topic hz /sim/laksa/scan
sudo docker compose -f docker-compose.c1.yaml exec -T wall-follow \
  /usr/local/bin/c1_entrypoint.sh timeout 8 ros2 topic hz /sim/laksa/motion_request
```

The `/sim/laksa/scan` invocation produced no rate line in the supplied
terminal transcript. The following six averages appeared after the
`motion_request` invocation:

```text
19.967, 19.977, 19.989, 19.993, 19.991, 20.001 Hz
```

Thus the motion-request stream was observed around 20 Hz in that existing
container. The later rebuilt-service scan windows are recorded below; the
request-rate observation still belongs to an unidentified older image. The local source branch head
is `7dd2bcd64a2fa8a406890456dd2795100e74ba91`, but no image rebuild or runtime
image/source identity accompanied this observation, so that SHA is not
attributed as the container's exact tested commit. The collision, rejected
moving-request/frozen-step, and launch-restart/fresh-episode checks also remain
unrun. At that earlier checkpoint, the overall gate remained **UNVERIFIED**.

## Operator collision and moving-request probe (2026-09-28)

The operator captured evidence in
`firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_humble_20260928T183631Z/`.
The saved host checkout SHA is
`b6f5bd0a799e594ea4a47b1ade4179e0586c7d22`; the collision container image ID
is
`sha256:d128d8d010d1b175a85ec6a97836274ac5c8685008b3bc180382343e4eaac233`.
The transcript does not include a build or label tying that image digest to
the saved host source SHA, so this is not a verified source-to-image mapping.

The operator captured episode status before and after publishing 20 mock
moving requests, then saved the launch logs:

```bash
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  ros2 topic pub --rate 20 --times 20 \
  /sim/laksa/motion_request ackermann_msgs/msg/AckermannDriveStamped \
  '{drive: {speed: 0.38, steering_angle: 0.2}}'
sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status
sudo docker logs wall-follow-collision
sudo docker compose -f docker-compose.c1.yaml run -d --no-deps \
  --name wall-follow-restart wall-follow \
  ros2 launch laksa_speed_race wall_follow_sim.launch.py collision_test:=false
sudo docker exec wall-follow-restart /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status
sudo docker logs wall-follow-restart
# The first echo ran before graph discovery completed. Follow up on the same
# live container and save the later startup log/status:
sudo docker logs --tail=100 wall-follow-restart
sudo docker exec wall-follow-restart /usr/local/bin/c1_entrypoint.sh \
  timeout 20 ros2 topic echo --once /sim/laksa/gym_status
```

The launch log explicitly reports `gym_collision` for episode
`546acfc1a992492b990639820f420b5b` at `gym_steps=1`. The status snapshots
have that same episode ID and step count; `rejected_terminal_requests` rises
from 32,691 to 32,796. `moving_probe.txt` shows 20 published requests at
0.38 m/s and 0.2 rad. The rejection counter also includes any continuing
controller requests during the observation interval, so the 105-count delta is
not attributed solely to the 20-message probe. No later Gym step was observed.
Because simulator motion advances through Gym steps, this supports the
simulation's terminal no-motion behavior; the capture has no separate
applied-motion topic trace.

The restart command created container
`4eabcbf4401fcd5f2bb2b7001ea94874fd899b9ba8e2221afbdf40661abeaa80`. The
first status query ran before DDS discovery completed and warned that the
topic was not published yet. A later query on the same live container
(`wall-follow-restart Up 6 minutes`) succeeded. Its startup log records
`episode_started id=de3fd4b1a3ec445191473d2cff5073de`, distinct from the
collided episode ID. The status reports that same new ID, 37,209 Gym steps,
zero rejected requests, and `terminal_reason: null`. This verifies that
restarting the launch created a new active episode. The initial step counter
was not captured immediately at startup.

The compact raw capture files are committed beside this record, including the
initial unavailable-topic response and the later active-episode status in
`restart_status_initial.yaml`, `restart_status.yaml`, and
`restart_followup.txt`. The overall ROS gate remains **PARTIAL / UNVERIFIED**: the later Dell
transcript records scan rates, but the rebuilt-image motion-request rate and
source-to-image mapping are still unverified. See the
evidence directory's `collision.log`, status snapshots, `moving_probe.txt`,
`restart.log`, `restart_followup.txt`, `source_sha.txt`, and `image_id.txt`.
The full capture command sequence is in
[`capture_commands.sh`](../../firmware/esp32-s3/jetson/laksa_speed_race/results/wall_follow_humble_20260928T183631Z/capture_commands.sh).

## Offline replay preparation checks

These checks exercised only the portable controller and fake LaserScan-shaped
objects; they did not import ROS 2, open a bag, or publish any ROS topic.

```bash
cd firmware/esp32-s3/jetson/laksa_speed_race
PYTHONPATH=. python3 -m unittest discover -s test -p 'test_wall_follow_scan_adapter.py' -v
PYTHONPATH=. python3 -m unittest discover -s test -p 'test_wall_follow_core.py' -v
PYTHONPATH=. python3 -m unittest discover -s test -p 'test_wall_follow_interfaces.py' -v
python3 -m compileall -q laksa_speed_race launch test setup.py
```

Results: adapter/export/preflight 5/5 PASS; core 10/10 PASS; interface
isolation/config 2/2 PASS; `compileall` PASS. The recorded synthetic preflight
used 12 intervals at 12.8 Hz and 1,800 values per scan, with 258 `inf` values
(14.3%). Requests stayed within 0–0.38 m/s and −0.288…+0.288 rad; 9/12 were
moving after the recovery gate. An all-invalid scan produced a zero-speed,
zero-steering brake-intent request (`too_many_invalid_ranges`); a 0.25 s stale
header produced the same bounded stop (`stale_scan_header`). The complete
request series is in
`results/wall_follow_10mm/laser_scan_adapter_preflight.json`. These are
synthetic adapter results only; measured A6 replay remains **UNVERIFIED**.

## Dell host build, live scan, and forced collision (operator transcript, 2026-09-28)

These observations came from the operator's Dell terminal using
`sudo docker`. The host SHA, collision image ID, and compact collision/restart
artifacts are saved in the evidence directory referenced above; the transcript
does not prove that the image was built from that SHA. The restricted Codex
runner cannot access the Dell Docker socket.

After the source-side OpenCV runtime-library fix in
`b6f5bd0a799e594ea4a47b1ade4179e0586c7d22` (installing `libgl1` and
`libglib2.0-0`), the operator's Docker Compose output reported the
`laksa_speed_race-wall-follow` image **Built** (211.1 s) and the
`wall-follow` container **Started** (13.9 s). A manual `python3 -c` probe
reached `cv2` successfully, then raised `AttributeError` because the
probe typed `cv2._version_` instead of `cv2.__version__`. That typo is not
an OpenCV import failure. The launch log independently showed both ROS
processes starting and the Gym mock announcing:

```text
episode_started id=9d78406528364079b0cd4cdf0c5045c6
profile=continuous_wall_30in seed=101 collision_test=False initial_x_m=1.000
```

The operator then observed this episode's `/sim/laksa/gym_status` with
`gym_steps=227059`, `rejected_terminal_requests=0`, and
`terminal_reason=null`. The large step count measures time spent stepping,
not traversal or lap completion. In that running container,
`ros2 topic hz /sim/laksa/scan` produced these ten windows (seconds for
interval statistics):

| Window | Average Hz | Min interval | Max interval | Std dev | Samples |
|---:|---:|---:|---:|---:|---:|
| 1 | 19.969 | 0.046 | 0.053 | 0.00168 | 21 |
| 2 | 19.983 | 0.044 | 0.055 | 0.00221 | 41 |
| 3 | 19.979 | 0.044 | 0.055 | 0.00202 | 61 |
| 4 | 19.988 | 0.044 | 0.055 | 0.00188 | 82 |
| 5 | 19.991 | 0.044 | 0.055 | 0.00171 | 103 |
| 6 | 19.991 | 0.043 | 0.055 | 0.00172 | 124 |
| 7 | 19.995 | 0.043 | 0.055 | 0.00165 | 145 |
| 8 | 19.987 | 0.043 | 0.055 | 0.00163 | 165 |
| 9 | 19.994 | 0.043 | 0.055 | 0.00164 | 186 |
| 10 | 19.995 | 0.043 | 0.055 | 0.00156 | 207 |

These ten windows verify an approximately 20 Hz ROS scan stream in the
operator's rebuilt container. The earlier 19.967–20.001 Hz motion-request
observations belonged to an unidentified older image; the request rate has not
yet been remeasured on the rebuilt image.

The operator started a separate simulation-only container named
`wall-follow-collision` with `collision_test:=true`. Its first supplied
`/sim/laksa/gym_status` excerpt showed episode
`546acfc1a992492b990639820f420b5b`, `gym_steps=1`, and
`rejected_terminal_requests=93`; the displayed `terminal_reason` field
was truncated after `gym_col...`. The container log supplies the complete
terminal reason and placement:

```text
episode_started id=546acfc1a992492b990639820f420b5b
profile=continuous_wall_30in seed=101 collision_test=True initial_x_m=0.150
gym_collision: simulator episode latched
id=546acfc1a992492b990639820f420b5b gym_steps=1; restart launch to reset
```

Together with the earlier collision/probe record, these observations establish
a real ROS 2 Humble scan stream, forced Gym collision, unchanged step count
through 20 nonzero requests, and a distinct active episode after restart in
isolated Docker simulation. The rejected-request count rose by 105 across the
status interval; because the controller was also publishing, that delta cannot
be assigned only to the 20-message probe. No separate applied-motion trace
was captured. The prior 19.967–20.001 Hz motion-request rate came from an
unidentified image, so the rebuilt-image request rate and image/source mapping
remain unverified. Overall state is **PARTIAL / UNVERIFIED**. Real A6 scan
replay remains **UNVERIFIED** pending the scan-only export, measured LiDAR
transform, and recorded request trace. No physical car, device, or
`/laksa/command` topic was involved.
