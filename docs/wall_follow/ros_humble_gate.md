# ROS 2 Humble execution gate

Date: 2026-09-28 UTC. Scope: isolated simulation only.

The execution host was checked without starting any hardware or production
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

Therefore `wall_follow_sim.launch.py` was not run. No ROS-observed scan rate,
motion-request rate, collision latch, post-terminal request rejection, blocked
terminal stepping, or fresh episode after launch restart is claimed. Portable
focused tests exercise the terminal authority state machine, but that is not a
substitute for executing the ROS wrapper and pinned Gym together.

Gate state: **UNVERIFIED**. The next suitable Docker/ROS 2 Humble host must run
the isolated launch, measure both topic rates, force a Gym collision, verify
that later requests cannot move or step that terminal episode, terminate the
launch, and verify that a fresh launch creates a fresh episode. No physical
command topic or car device is part of this gate.

## Dell Docker attempt (2026-09-28)

The latest `codex/wall-follow-gym` source available for this attempt was
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

The Compose service was not built or launched. No ROS nodes ran, so there are
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
implemented on the branch. They have not run in Humble: no measured topic
rates, Gym collision, rejected-request count, frozen step count, or new
episode ID after restart is claimed. Gate state remains **UNVERIFIED**.

The tested offline replay/collision-probe source is
`d325f12ed721e407d9e2a2b6f23607e3d8fc6585`. The focused command results were:
scan adapter/export/preflight 5/5 PASS, controller core 10/10 PASS, interface
isolation/config 2/2 PASS, and `compileall` PASS. Those local checks cover the
portable path and static interface contracts, not ROS node execution.

## Dell topic-rate observation (operator terminal, 2026-09-28)

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
container; **the scan rate is still unmeasured**. The local source branch head
is `7dd2bcd64a2fa8a406890456dd2795100e74ba91`, but no image rebuild or runtime
image/source identity accompanied this observation, so that SHA is not
attributed as the container's exact tested commit. The collision, rejected
moving-request/frozen-step, and launch-restart/fresh-episode checks also remain
unrun. The overall gate remains **UNVERIFIED**.

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

These observations came from the operator's normal Dell terminal using
`sudo docker`. The restricted Codex runner still cannot access the Dell
Docker socket. The operator supplied terminal excerpts in conversation;
the complete host-generated YAML/log files and image ID have not yet been
added to this repository. Do not attribute the runtime image to a source SHA
until its build checkout SHA and image ID are captured together.

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
`ros2 topic hz /sim/laksa/scan` produced these ten average-rate windows:

```text
19.969, 19.983, 19.979, 19.988, 19.991,
19.991, 19.995, 19.987, 19.994, 19.995 Hz
```

Reported inter-message extremes across these windows were 0.043–0.055 s;
the last output used a 207-message window. This verifies an approximately
20 Hz ROS scan stream in the operator's rebuilt container. The earlier
19.967–20.001 Hz motion-request observations belonged to an unidentified
older image; the request rate has not yet been remeasured on this rebuilt
image, and rate alone does not prove nonzero motion.

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

Thus a real ROS 2 Humble launch, scan stream, forced Gym collision, and
post-terminal request rejection were observed in isolated Docker simulation.
The already-positive rejection count can include the controller's own
post-collision requests; it does not prove that deliberate nonzero probe
requests were delivered or rejected. No before/after moving-probe snapshots,
unchanged step count *after that probe*, or fresh episode after a restart
have been supplied. The current ROS gate remains **PARTIAL / UNVERIFIED**
until those outputs and source/image identity are captured. Real A6 scan
replay remains **UNVERIFIED** pending the scan-only export, measured LiDAR
transform, and recorded request trace. No physical car, device, or
`/laksa/command` topic was involved.
