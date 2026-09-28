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
physical command topic was accessed.
