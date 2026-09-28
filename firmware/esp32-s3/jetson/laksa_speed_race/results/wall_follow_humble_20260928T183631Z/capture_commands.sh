GATE_DIR="$PWD/results/wall_follow_humble_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$GATE_DIR"

git rev-parse HEAD > "$GATE_DIR/source_sha.txt"
sudo docker inspect --format '{{.Image}}' wall-follow-collision > "$GATE_DIR/image_id.txt"

sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status \
  > "$GATE_DIR/collision_before.yaml"

sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  ros2 topic pub --rate 20 --times 20 \
  /sim/laksa/motion_request ackermann_msgs/msg/AckermannDriveStamped \
  '{drive: {speed: 0.38, steering_angle: 0.2}}' \
  > "$GATE_DIR/moving_probe.txt"

sudo docker exec wall-follow-collision /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status \
  > "$GATE_DIR/collision_after.yaml"

sudo docker logs wall-follow-collision > "$GATE_DIR/collision.log" 2>&1

sudo docker compose -f docker-compose.c1.yaml run -d --no-deps \
  --name wall-follow-restart wall-follow \
  ros2 launch laksa_speed_race wall_follow_sim.launch.py collision_test:=false

sudo docker exec wall-follow-restart /usr/local/bin/c1_entrypoint.sh \
  timeout 10 ros2 topic echo --once /sim/laksa/gym_status \
  > "$GATE_DIR/restart_status.yaml"

sudo docker logs wall-follow-restart > "$GATE_DIR/restart.log" 2>&1

sudo docker logs --tail=100 wall-follow-restart
sudo docker exec wall-follow-restart /usr/local/bin/c1_entrypoint.sh \
  timeout 20 ros2 topic echo --once /sim/laksa/gym_status \
  > "$GATE_DIR/restart_status.yaml"
cat "$GATE_DIR/restart_status.yaml"
