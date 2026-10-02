# LAKSA offline field kit — October 2

This is a local, read-only recorder for an Ubuntu 22.04 / ROS 2 Humble Orin.
It discovers live topics, records a selected low-bandwidth set on **the Orin's own disk**,
and writes a snapshot and event notes. It never publishes a ROS topic, starts the car,
or modifies the control stack. The Dell is for SSH while parked, copying evidence,
and offline review. Recording continues after SSH disconnects.

## Before leaving home

1. Copy this folder to both computers while connectivity is available (or use USB).
2. On the Orin, check `python3 --version`, `ros2 bag record --help`, free disk space,
   and the workspace setup path. The script sources `/opt/ros/humble/setup.bash`
   plus each `--setup` path supplied before the action.
3. While the normal stack is running **parked**, perform a 20-second practice
   recording and `stop`. Inspect `postflight.json` for `bag_info.exit_code: 0`
   and nonzero messages on `/scan`, commands, and vehicle state where active.
4. Save a known control-stack commit/config and the physical stop arrangement.
   Do not connect the recording script to an actuator topic.

Preflight saves publisher/QoS details for `/laksa/command`, `/scan`, and
`/tf_static`, reports duplicate node names, and tries to capture a scan header,
static TF sample and VESC state. Zero command publishers is expected for
actuator-disabled reconnaissance; more than one needs investigation. These
checks are diagnostic and do not certify physical readiness.

Confirm measured base-to-lidar and base-to-camera transforms and one odometry
authority. A `/tf_static` topic or message does not prove the tree is correct.
If a transform is missing, save actual frame names and measured mounting
offsets/orientations for reconstruction at home. Preserve the scans even if
full mapping cannot yet be replayed. Do not publish guessed transforms or
add a second authority to an existing tree.

Commands on the Orin (replace paths and run labels as appropriate):

```bash
python3 fieldkit.py --setup ~/laksa_ws/install/setup.bash preflight --git-dir ~/laksa_ws/src
python3 fieldkit.py --setup ~/laksa_ws/install/setup.bash start night1-obstacle --dry-run
python3 fieldkit.py --setup ~/laksa_ws/install/setup.bash start night1-obstacle
python3 fieldkit.py mark night1-obstacle "entered first narrow turn"
python3 fieldkit.py --setup ~/laksa_ws/install/setup.bash stop night1-obstacle
python3 fieldkit.py report night1-obstacle
```

Replace `~/laksa_ws/install/setup.bash` with the **actual** installed overlay;
omit `--setup` if the needed message types already resolve in the base environment.
Unique names protect prior run data. Default output is `~/laksa_field_runs/<name>/`.
The recorder requires `/scan` and at least 4 GiB free by default; adjust
`--min-free-gb` if a shorter test and storage budget warrant it. A snapshot
records the ROS topic graph and host configuration. `stop` sends SIGINT to the
specific recorder and captures `ros2 bag info` plus recent kernel messages.
SQLite storage is explicitly selected. A transient-local QoS override for
`/tf_static` requests retained messages published before recording.

The selected topics include `/scan`, state, VESC, IMU, TF, pose, requested and
applied command paths, diagnostics, stop and mission state **when advertised**.
No image or point-cloud topics are included, to avoid competing with the live
pipeline and filling the disk. An SVO can be recorded by the **already running**
ZED wrapper if its recording service has been identified and tested; do not
start a second camera process just for this field visit. Record the SVO path in
the event notes and transfer it with the bag. SVO is separate from the ROS bag.
If the **existing** wrapper advertises `/zed/zed_node/start_svo_rec`, its
documented interface is:

```bash
ros2 service list -t | grep start_svo_rec
ros2 service call /zed/zed_node/start_svo_rec zed_msgs/srv/StartSvoRec \
  "{svo_filename: '/home/ubuntu/laksa_field_runs/night1-obstacle/camera.svo2', compression_mode: 0}"
ros2 service call /zed/zed_node/stop_svo_rec std_srvs/srv/Trigger
```

Replace `/home/ubuntu` with the real Orin user's home. Use `stop_svo_rec`
before transferring. Check the service response and file size; if the service
is absent, stay with the ROS bag and photos.

## Optional Dell connection

Use a preconfigured, trusted local Ethernet link or established private Wi-Fi,
only if track rules permit it. Verify SSH **before** the run with a known host
key. `ssh orin@<known-ip>` can run `python3 ... mark` and read a health summary,
but the car must not depend on the connection. Do not build an HTTP or MQTT
command bridge tonight: it adds another live command path and supplies no
benefit to local evidence capture. If wireless is unavailable, make spoken
phone-video markers and add notes afterward with approximate timestamps.

After the car is parked and recording has stopped, copy the entire directory:

```bash
rsync -a --partial orin@<known-ip>:~/laksa_field_runs/night1-obstacle/ ~/laksa_field_runs/night1-obstacle/
ros2 bag info ~/laksa_field_runs/night1-obstacle/bag
python3 review.py ~/laksa_field_runs/night1-obstacle
```

If there is no network, transfer the whole directory by removable drive.
Do not copy a live SQLite bag. Keep originals on the Orin until the copied
`metadata.yaml`, `.db3` file(s), and `events.jsonl` have been checked.
The summary reports counts, spans, average rates, largest receipt-time gaps
for scan/control/state/odometry topics, and selected topics receiving zero
messages. Receipt gaps are clues; sensor header timestamps need separate
inspection. Commands may legitimately be absent during reconnaissance.

## One-hour visit sequence

| Minutes | Work |
| --- | --- |
| 0–10 | Walk permitted area; measure widths, turn radius hints, obstacle heights, surfaces, slope, lighting; photograph from car-height and overhead with a scale reference. |
| 10–20 | Parked preflight; start a unique bag; mark a visible clock/video sync event. Confirm data is actually accumulating. |
| 20–35 | With actuators disabled and sensors powered, move the car slowly along an accessible section for ZED SVO if the existing camera setup can record reliably. A LiDAR/ROS bag can capture geometry while walking. |
| 35–45 | Continue stationary scans at each section and collect missing dimensions. Keep actuators disabled throughout visit one. |
| 45–60 | Park, stop recording, inspect `bag info`, copy, photograph final configuration and any contact marks. |

Use visit one for geometry, perception, localization, and timing data with no
motor commands. Manually pushed wheel odometry is not ground truth; annotate
the collection mode. Night photos
are for geometry and annotations; daylight camera performance needs a new
daylight observation. Do not infer a physical stop from a ROS status topic.

## Home review and second visit

First check time coverage, nonzero topic counts, and event notes. Then inspect
weak scan geometry, pose/TF consistency and data gaps in each section, along
with VESC state and health/agent logs. If command data exists, compare candidate
versus `/laksa/command` without replaying it onto the car. Compare car width
and course clearance with the photos and measurements. Make one hypothesis,
one proposed adjustment, and an explicit check for visit two. Prefer a repeat
of the same short segment at the same speed to distinguish a real improvement
from a different trajectory. A second visit can instead sample the other course
if visit one's result is clear and access permits it.
Any powered drive on visit two requires the team's independently verified
physical stop and bounded control path; the recorder does not establish either.

Never replay recorded `/laksa/command` into a connected physical ROS graph.
Run bag replay and controller experiments on the Dell in an isolated ROS domain
with no actuator subscriber, or extract the bag to an offline analysis format.
