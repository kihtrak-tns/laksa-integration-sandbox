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
