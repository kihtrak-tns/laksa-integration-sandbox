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

Gym's collision flag checks the simulated vehicle footprint. The separate
clearance metric samples all four rectangle edges at intervals of at most
20 mm; it is a perimeter estimate, not an exact polygon-to-occupancy distance.
Earlier manifests used four corners and retain their historical values only.
Map truth and pose truth are used only for metrics and run termination; the
controller receives only scan data.

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
Gym collision. The revised 10 mm occupancy resolution makes the rendered
19/20/21-inch entries distinct; each manifest records the rasterized width.
The earlier 20 mm maps rasterized 20 and 21 inches identically. The revised
geometry passed the recorded full Gym campaign but does not claim the real
course shape.

Fault cases inject controller crash, silent publisher, frozen and delayed
scans, malformed scan, sensor dropout, command burst, restart, a forward
obstacle, and an obstacle in a wall recess. Front hazards are evaluated before
any moving opening-bridge request. The mock authority owns an independent
request freshness timer and continues stepping the simulator while it ramps
speed to zero. Each trace records scan/request events, requested and applied
speed/steering, stop timing, and simulated stop distance.

In the ROS mock, a collision or terminal Gym state latches the episode and
rejects further requests. Restart the isolated launch to reset both Gym and
controller. The headless campaign creates fresh instances for each case. The
ROS behavior remains unexecuted on Humble; only the pure-Python latch was
tested. For static obstacles, the revised response clock starts at the first
scan placing an object within front slowdown distance. Earlier traces began
that clock at the explicit stop request and cannot establish perception
response latency.

Corridor traversal, safe stop, and corner completion are reported separately.
No closed-loop race lap is executed, so lap completion remains `UNVERIFIED`;
these runs are not three-lap or speed-course validation.

The prior 20 Hz-control evidence is stored under `results/wall_follow_20hz`.
It predates the revised maps, clearance metric, and obstacle timing.
The original 100 Hz-controller campaign remains unchanged under
`results/wall_follow` for comparison.

The current review-fix campaign uses 10 mm occupancy cells and is stored under
`results/wall_follow_10mm`. Its tested source is
`290a2f3b22b3dc12443535fec7d2545e47ca5dcf`; its configuration SHA-256 is
`b1fa0b84e1b36a947eae3f59dfb55651fc50a74684aa6534b4280e14698913e7`.
Rendered entry widths are 0.48, 0.50, 0.54, and 0.76 m for the nominal
19-, 20-, 21-, and 30-inch profiles. The minimum recorded perimeter-sampled
clearance estimate is 0.0483 m.

Obstacle timing begins when a scan first places the obstacle inside the 0.75 m
slowdown threshold. The manifest separately records detection-to-stop-request,
detection-to-zero-applied, stop-request-to-zero-applied, and distance after the
stop request. A safe stop remains distinct from traversal or lap completion.

## Known gaps

- Neither Windows nor Ubuntu-22.04 WSL on the execution host exposed Docker or
  ROS 2 Humble, so the ROS launch wrapper is syntax/interface tested but was
  not executed end to end.
- No committed real RPLIDAR bag exists at the reviewed Orin head.
- No physical braking, timeout, steering endpoint, odometry, eRPM, RJ45 stop,
  or final publisher-ownership result exists.
- The opening bridge is bounded, low-speed simulation logic; it must not be
  promoted without real scan replay and the physical safety gates.
