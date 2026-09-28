# Wall-follow simulation model card

## Scope and claim boundary

This model exists only to exercise a scan-driven controller and a mock motion
request interface. It is not a digital twin and no result in this directory is
evidence that the physical LAKSA car is safe, correctly wired, or correctly
calibrated. The simulator never publishes `/laksa/command` or `/cmd_vel`.

Source baseline is
`competition/speed-race-track@21588774eef8023811e751019b13abc9a43b692e`.
The dynamics engine is `f1tenth_gym@bdaec1420c3b0f103858d289866d0d4e2e597c30`;
the ROS reference pin is
`f1tenth_gym_ros@08395766c4d9dc5a763381f1dd6fa4a3d68df66e`.
The exact controller and watchdog values are versioned in
`config/wall_follow_v1.json` and hashed into every run manifest.

## Geometry and dynamics

The unchanged pinned Gym kinematic single-track model runs with RK4 at 100 Hz.
The simulation proxy uses 0.324 m wheelbase, 0.568 x 0.296 m collision body,
body-center x offset 0.135 m, 3.75 kg upstream-default mass, and symmetric
steering limits of +/-0.288 rad. Only wheelbase/body dimensions have historical
measurement support in the sandbox. Mass, inertia, friction, acceleration,
servo response, braking, and symmetric steering are proxy assumptions.

The full collision footprint, not the base-link point, is used for clearance
metrics. Map truth and pose truth are used only for metrics and run termination;
the controller receives only scan data.

## Scan model

Gym ray-casts 1,080 beams over -135 to +135 degrees, 0 to 30 m, with 2 mm
Gaussian noise. Gym dynamics and the request watchdog step at 100 Hz; a new
scan is delivered to the controller at 20 Hz and the controller can publish at
most one request for each delivered scan. Applied requests are held between
scans. This matches the ROS wrapper cadence instead of giving the headless
controller an artificial 100 Hz scan stream. The simulation mount is
x=0.31542 m, y=0, yaw=0.
This intentionally differs from the inherited `laksa_proxy_v0.yaml` pi-yaw:
in the pinned Gym, pi yaw plus a 270-degree field of view creates a 90-degree
forward blind sector and cannot support forward-obstacle stopping. The real
RPLIDAR mounting transform and angular convention remain unknown and require a
real bag/TF capture before any car adapter is designed.

## Scenarios and acceptance

Generated maps cover a 30-inch corridor with a 0.8 m right-wall recess,
continuous 19-, 20-, and 21-inch corridors, and a continuous-wall 90-degree
left corner. Each nominal map runs five fixed seeds from three lateral/heading
perturbations. A pass requires reaching that scenario's metric finish without
Gym collision. The 19/20/21-inch cases cover the stated 20 +/- 1 inch
uncertainty; they do not claim the real course geometry.

Fault cases inject controller crash, silent publisher, frozen and delayed
scans, malformed scan, sensor dropout, command burst, restart, a forward
obstacle, and an obstacle in a wall recess. Front hazards are evaluated before
any moving opening-bridge request. The mock authority owns an independent
request freshness timer and continues stepping the simulator while it ramps
speed to zero. Each trace records scan/request events, requested and applied
speed/steering, stop timing, and simulated stop distance.

Corridor traversal, safe stop, and corner completion are reported separately.
No closed-loop race lap is executed, so lap completion remains `UNVERIFIED`;
these runs are not three-lap or speed-course validation.

## Known gaps

- Neither Windows nor Ubuntu-22.04 WSL on the execution host exposed Docker or
  ROS 2 Humble, so the ROS launch wrapper is syntax/interface tested but was
  not executed end to end.
- No committed real RPLIDAR bag exists at the reviewed Orin head.
- No physical braking, timeout, steering endpoint, odometry, eRPM, RJ45 stop,
  or final publisher-ownership result exists.
- The opening bridge is bounded, low-speed simulation logic; it must not be
  promoted without real scan replay and the physical safety gates.
