#!/usr/bin/env bash
# Managed by AG-Products/notion-cicd
set -eo pipefail

PROFILE="${AG_BUILD_PROFILE:-generic}"
ROS_DISTRO="${AG_ROS_DISTRO:-humble}"
ROS_PACKAGE="${AG_ROS_PACKAGE:-}"

ros_build() {
  local mode="$1"
  docker run --rm \
    -e ROS_DISTRO="$ROS_DISTRO" \
    -e ROS_PACKAGE="$ROS_PACKAGE" \
    -e BUILD_MODE="$mode" \
    -v "${GITHUB_WORKSPACE:-$(pwd)}:/repo" \
    "ros:${ROS_DISTRO}" \
    bash -c '
      set -eo pipefail
      source "/opt/ros/${ROS_DISTRO}/setup.bash"
      mkdir -p /ws/src
      if [ "$BUILD_MODE" = "ros2" ]; then
        ln -s /repo "/ws/src/${ROS_PACKAGE}"
        cd /ws
        colcon build --packages-select "${ROS_PACKAGE}"
      else
        cp -a /repo/. /ws/src/workspace/
        cd /ws
        colcon build
      fi
    '
}

case "$PROFILE" in
  ros2)
    if [ -z "$ROS_PACKAGE" ]; then
      echo "AG_ROS_PACKAGE is required for ros2 profile" >&2
      exit 1
    fi
    ros_build ros2
    ;;
  ros2-workspace)
    ros_build ros2-workspace
    ;;
  generic)
    echo "AG-Products generic CI profile"
    test -d .
    find . -maxdepth 2 -type f | head -20
    ;;
  *)
    echo "Unknown AG_BUILD_PROFILE: $PROFILE" >&2
    exit 1
    ;;
esac
