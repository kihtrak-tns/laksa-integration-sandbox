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
```

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
