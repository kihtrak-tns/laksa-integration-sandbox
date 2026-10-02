# Codex task: prepare the Dell for LAKSA field kit v2

Execute this setup on the Dell's native Ubuntu 22.04. The first track visit is
actuator-disabled reconnaissance. Prioritize a working offline acquisition and
copy workflow within roughly 45 minutes. Complete useful local work while any
Orin connection or physical-console step is pending. Report genuine blockers
without declaring untested stages ready.

## Scope and locations

Set up the Dell as an SSH client, run-transfer host and Python bag-review host.
The recorder runs on the Orin with its existing ROS 2 Humble environment.
Basic Dell review uses Python's standard library; it needs neither ROS nor a
ZED SDK installation. Existing Dell ROS/RViz can be used later in an isolated
domain, but new ROS, Unity, ML, CUDA and simulator installs are outside this
night's required setup. All field commands must work without internet or an
active Codex session.

Use `~/laksa-fieldkit` for installed kit files and `~/laksa_field_runs` for
copied runs on the Dell. Discover the real Orin user/home, installed ROS overlay
and repository path; do not assume `/home/ubuntu` or `~/laksa_ws`. Preserve
existing files/configurations and keep timestamped backups before edits.
Do not publish to actuator/mode/stop topics, flash firmware, alter VESC or
control settings, restart running sensor/control services, or run bag playback
on the car. Local SSH/network setup, kit deployment and recording are authorized.

## 1. Inventory and essential dependencies

Check OS, Python, disk free, existing kit/repo checkout, SSH client, rsync,
NetworkManager, interfaces/routes, clock status and existing ROS installs.
Install only missing essential packages while home internet is available:
`openssh-client`, `rsync`, `python3`, and `unzip` if needed. Retain existing
NetworkManager. Do not run a distribution upgrade. Sudo/password entry belongs
to the user at the terminal; never save credentials in scripts or reports.
Reserve at least 10 GiB on the Dell if available and report actual capacity.

Use the bundled v2 files. If no bundle exists, obtain only `fieldkit.py`,
`review.py`, and `README.md` from repository
`kihtrak-tns/laksa-integration-sandbox` at commit
`1d38acb0c2f5b7fe2215dc079765f1bf57841123`, path `fieldkit/`.
Verify these SHA-256 values before deployment:

```text
6a62dd0547cc6b667a3363829cb5e08c5da4f7d35417b0cd6a3878e39aad8225  fieldkit.py
5f59a6bc4b5d1381aef8018f743a459bab9166e85418f742ab84e0c5707fa189  review.py
3cced1f12849528fdd5d226d362451e5e9563ffe132925460aaf51995ff7cad9  README.md
```

## 2. Establish SSH while at home

Discover the Orin's known address and username from existing configuration;
if unavailable, ask the user once to run `whoami`, `hostname -I`, and
`systemctl is-active ssh` at its console and share the results. Give that
physical-console step while continuing Dell setup. If SSH server is absent,
have the user install `openssh-server` on the Orin while online and enable
`ssh`. The Dell needs only the client. Do not disable the firewall; if blocked,
add a narrow SSH rule for the Dell's address and document it.

Verify the SSH host-key fingerprint against the Orin's console output of
`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` before first acceptance.
Do not bypass host-key verification or silently replace a changed key.
Use an existing suitable key or create a dedicated Ed25519 key without
overwriting one; arrange ssh-agent/passphrase or interactive login with the
user. Use `ssh-copy-id -i <chosen-public-key>` if authorized login is available.
Keep private keys on the Dell. Add a specific `laksa-orin` SSH alias with the
verified user, host, chosen identity, reasonable connect timeout and keepalive.
Verify with `ssh laksa-orin 'hostname; whoami; date -u'`.

## 3. Prepare the offline connection

Prefer a direct Ethernet cable for parked setup/copy at the track. Inspect
both machines' interfaces and existing routes. If unused, choose a dedicated
subnet such as 192.168.77.0/24: Dell .1, Orin .2. Create separately named
NetworkManager manual profiles bound to the actual Ethernet interfaces,
with `ipv4.never-default yes`, no gateway/DNS and
`connection.autoconnect no`. Preserve existing Wi-Fi and normal Ethernet
profiles. Document activation and rollback commands.

Configure/activate the Orin profile from its physical console if remote
activation would interrupt the only current session. Create a separate
`laksa-orin-wired` SSH alias. Test SSH and a small file copy with Wi-Fi
temporarily disconnected through the normal UI, then restore it. Do not
turn off a shared access point or disconnect an active SSH session blindly.
If a cable/interface is unavailable, test the existing car hotspot if present;
otherwise document USB-drive transfer and local Orin recording as the fallback.
Do not promise an untested offline connection.

## 4. Deploy the kit and preserve the car environment

Copy the verified kit to `~/laksa-fieldkit` on the Orin and create its
`~/laksa_field_runs`. Confirm the Orin file hashes. Inspect its actual ROS
setup paths and require that custom `laksa_interfaces` resolve in that overlay.
Verify `ros2 bag record --help`, SQLite storage and the QoS override option.
Do not rebuild or replace the running car stack. Record its real repo HEAD
and dirty status if found. Capture both clocks and their offset; do not step
the Orin clock during recording. Events and bag receipt timestamps use the
same Orin clock.

## 5. Make short Dell commands

Create a small local launcher, usable without Codex, with commands:
`preflight`, `start RUN`, `mark RUN NOTE`, `stop RUN`, `fetch RUN`, `review RUN`,
and `status RUN`. It must call the kit on the Orin over the selected SSH alias
with the verified overlay paths. Validate run labels and safely quote remote
arguments, including notes with spaces/apostrophes. Reuse `fieldkit.py` rather
than creating another recorder. Save private connection details locally.

`fetch` must refuse a live recorder, copy the complete finalized run including
SVO if present with rsync (`--partial`, no `--delete`), and preserve originals.
Check remote/local file lists, sizes and SHA-256 of finalized bag files and
metadata before declaring the copy verified. Write the review JSON locally.
Make a one-page local `FIELD_COMMANDS.md` with exact ready-to-run commands and
the removable-drive fallback. Ensure copied SQLite bags can be reviewed using
`python3 review.py RUN_DIRECTORY` with no ROS installation on the Dell.

## 6. Verify once while parked, actuators disabled

With the already-running sensor stack, run preflight and a unique 20-second
practice bag. Add a marker, disconnect the Dell session, reconnect, inspect
status, stop the recorder, fetch the run and review it. Confirm nonzero scans,
any available TF/state topics, expected counts, marker presence and finalization.
Zero command publishers/messages is appropriate for reconnaissance. Multiple
command publishers or conflicting TF authorities require investigation.
Missing transforms/IMU must be reported without inventing them.

If the existing ZED wrapper is healthy, inspect its advertised recording service
and installed service schema. Test a brief SVO via that process only, stop it,
and verify recording and copy. Report this as optional if unavailable, codecs
fail, or it disrupts telemetry. Do not open a second live camera process.
Keep all activity here limited to recording/observing; do not enable motion.

## Deliverable

Save local `DELL_SETUP_STATUS.md` with: dependency versions, kit hashes,
working SSH alias, tested offline connection, actual overlay paths, free disk,
practice bag counts/gaps, verification results, unresolved blockers and exact
field commands. State separately what was verified versus merely configured.
If sensors or the Orin are unavailable, finish Dell setup, deploy the kit when
possible, and list the precise remaining on-car check. No claim of race readiness.
