# Updated speed-race base integration

Date: 2026-09-28 UTC. Scope: source integration and simulation-only checks.

## Identity

- Wall-follow pre-merge head: `6a685098163e8a4abcd7fbb39dea6c640b74f3cd`
- Updated base: `f9676915ff71d3e7f22ed588e8054e5ce7cf9c72`
- Common ancestor: `21588774eef8023811e751019b13abc9a43b692e`
- Merge commit: `92ed803cdb9e331312139b888c6da4ebf195f25f`

## Conflict and resolution

`git merge --no-ff origin/competition/speed-race-track` produced one content
conflict, in `firmware/esp32-s3/jetson/laksa_speed_race/setup.py`. Both branches
had appended console scripts to the same list. The resolution retains all five
entries involved in the conflict:

- official base: `c1_historical_replay`;
- wall-follow branch: `wall_follow_controller`, `wall_follow_gym_mock`,
  `wall_follow_campaign`, and `wall_follow_replay`.

All other official C1.2d MPPI and historical-replay changes merged without a
manual resolution. No rebase, force push, branch rewrite, or file selection
discarded either side's work. A packaging regression now asserts that both
scopes' entry points remain installed.

## Checks actually run

From `firmware/esp32-s3/jetson/laksa_speed_race` on Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s test -p 'test_wall_follow_*.py' -v
.\.venv\Scripts\python.exe -m compileall -q laksa_speed_race launch test setup.py
.\.venv\Scripts\python.exe -m pytest -q `
  test\test_c1_packaging.py test\test_c1_isolation.py `
  test\test_wall_follow_core.py test\test_wall_follow_interfaces.py `
  test\test_wall_follow_maps.py test\test_wall_follow_replay.py `
  test\test_wall_follow_sim.py
.\.venv\Scripts\python.exe setup.py --name
```

Before the added merge regression, the focused pytest selection passed 22/22.
Afterward it passed 23/23. The 19 wall-follow tests passed independently,
`compileall` passed, and `setup.py --name` returned `laksa_speed_race`.

The broader `pytest -q` collection was also attempted: 48 passed, eight
Linux-only process-session tests skipped, and 19 failed. Eighteen failures are
downstream of frozen course/raceline SHA checks whose LF hashes do not match
this Windows CRLF checkout; one packaging failure initially reflected missing
`setuptools` in the ignored virtual environment and passed after installing
that declared build dependency. No frozen course asset or expected hash was
changed to manufacture a pass. C++/ROS/MPPI builds were not rerun on Windows.

## Runtime boundary

These integration checks did not start ROS, Gym, a physical publisher, or any
device. They do not change the previously recorded Gym campaign's source SHA
and do not qualify any physical-car gate.
