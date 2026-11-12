"""Mission server: feeds Nav2 ``NavigateToPose`` results into the mission FSM.

Design notes (these are the answers to the two questions a reviewer always asks):

1. *Why not a blocking loop?*  Goals are chained through action futures and a
   watchdog timer, so a hung navigator can never freeze the node's executor and
   the timeout branch stays reachable.
2. *Why is the FSM a separate module?*  So retry/timeout logic is covered by
   plain pytest in CI instead of "verified in Gazebo, trust me".

The server publishes ``/mission/state`` (JSON, one message per transition) and
``/mission/report`` (JSON, one message per finished mission), and optionally
appends every finished mission to a JSONL file for benchmarking.
"""

from __future__ import annotations

import json
import math
import os
from typing import List, Optional

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String

from warehouse_amr_mission.metrics import JsonlRecorder, MissionResult, summarize
from warehouse_amr_mission.mission_fsm import (
    NAV_STATES,
    TERMINAL_STATES,
    Event,
    InvalidTransition,
    Mission,
    MissionMachine,
    State,
)


def pose_stamped(frame_id: str, pose, stamp) -> PoseStamped:
    """``pose`` is ``(x, y, yaw)``; Nav2 wants a quaternion."""
    x, y, yaw = pose
    msg = PoseStamped()
    msg.header.frame_id = frame_id
    msg.header.stamp = stamp
    msg.pose.position.x = float(x)
    msg.pose.position.y = float(y)
    msg.pose.orientation.z = math.sin(yaw / 2.0)
    msg.pose.orientation.w = math.cos(yaw / 2.0)
    return msg


class MissionServer(Node):
    def __init__(self) -> None:
        super().__init__('mission_server')

        self.declare_parameter('missions_file', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('pick_duration_s', 2.0)
        self.declare_parameter('mission_timeout_s', 120.0)
        self.declare_parameter('max_nav_retries', 2)
        self.declare_parameter('loop', False)
        self.declare_parameter('autostart', False)
        self.declare_parameter('metrics_path', '')
        self.declare_parameter('tick_period_s', 1.0)

        self.frame_id = self.get_parameter('frame_id').value
        self.pick_duration_s = float(self.get_parameter('pick_duration_s').value)
        self.loop = bool(self.get_parameter('loop').value)
        self.autostart = bool(self.get_parameter('autostart').value)

        self._missions: List[Mission] = self._load_missions(
            self.get_parameter('missions_file').value)
        self._index = 0
        self._results: List[MissionResult] = []
        self._pick_deadline: Optional[float] = None
        self._goal_handle = None

        self._machine = MissionMachine(
            max_nav_retries=int(self.get_parameter('max_nav_retries').value),
            mission_timeout_s=float(self.get_parameter('mission_timeout_s').value),
        )

        metrics_path = self.get_parameter('metrics_path').value
        self._recorder = JsonlRecorder(metrics_path) if metrics_path else None

        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._state_pub = self.create_publisher(String, 'mission/state', 10)
        self._report_pub = self.create_publisher(String, 'mission/report', 10)

        period = float(self.get_parameter('tick_period_s').value)
        self._tick_timer = self.create_timer(max(0.1, period), self._on_tick)

        self.get_logger().info(
            f'mission_server up: {len(self._missions)} mission(s) loaded, '
            f'autostart={self.autostart}')

    # ------------------------------------------------------------------ setup
    def _load_missions(self, path: str) -> List[Mission]:
        if not path:
            self.get_logger().warn('missions_file is empty: nothing to execute')
            return []
        if not os.path.exists(path):
            self.get_logger().error(f'missions_file not found: {path}')
            return []
        with open(path, encoding='utf-8') as fh:
            raw = yaml.safe_load(fh) or {}
        entries = raw.get('missions', []) if isinstance(raw, dict) else raw
        missions = []
        for entry in entries:
            try:
                missions.append(Mission.from_dict(entry))
            except (KeyError, TypeError, ValueError) as exc:
                self.get_logger().error(f'skipping malformed mission {entry!r}: {exc}')
        return missions

    # ------------------------------------------------------------------- time
    def now_s(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    # ------------------------------------------------------------- transitions
    def _publish_transition(self, event: Event, previous: State, current: State) -> None:
        payload = {
            'mission_id': self._machine.mission.mission_id if self._machine.mission else None,
            'event': event.value,
            'from': previous.value,
            'to': current.value,
            'elapsed_s': round(self._machine.elapsed(self.now_s()), 3),
            'nav_goals': self._machine.nav_goals,
            'retries_used': self._machine.retries_used,
        }
        self._state_pub.publish(String(data=json.dumps(payload, ensure_ascii=False)))

    def _apply(self, event: Event) -> None:
        previous = self._machine.state
        try:
            current = self._machine.step(event, now=self.now_s())
        except InvalidTransition as exc:
            self.get_logger().error(str(exc))
            return

        self._publish_transition(event, previous, current)
        self.get_logger().info(f'{previous.value} --{event.value}--> {current.value}')

        if current is State.PICKING:
            self._pick_deadline = self.now_s() + self.pick_duration_s
        elif current in NAV_STATES:
            self._dispatch()
        elif current in TERMINAL_STATES:
            self._finish(current)

    # ---------------------------------------------------------------- dispatch
    def _dispatch(self) -> None:
        state = self._machine.state
        if state not in NAV_STATES or self._machine.mission is None:
            return
        if not self._client.server_is_ready():
            self.get_logger().debug('nav2 action server not ready yet, will retry on tick')
            return

        pose = self._machine.mission.pick if state is State.GO_TO_PICK else self._machine.mission.drop
        goal = NavigateToPose.Goal()
        goal.pose = pose_stamped(self.frame_id, pose, self.get_clock().now().to_msg())

        self._machine.mark_goal_sent()
        self.get_logger().info(f'goal -> {state.value} ({pose[0]:.2f}, {pose[1]:.2f})')
        self._client.send_goal_async(goal, feedback_callback=self._on_feedback).add_done_callback(
            self._on_goal_response)

    def _on_feedback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        self.get_logger().debug(
            f'distance remaining: {feedback.distance_remaining:.2f} m')

    def _on_goal_response(self, future) -> None:
        handle = future.result()
        if handle is None or not handle.accepted:
            self.get_logger().warn('goal rejected by navigator')
            self._apply(Event.NAV_FAIL)
            return
        self._goal_handle = handle
        handle.get_result_async().add_done_callback(self._on_nav_result)

    def _on_nav_result(self, future) -> None:
        wrapped = future.result()
        status = wrapped.status if wrapped is not None else GoalStatus.STATUS_ABORTED
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._apply(Event.NAV_OK)
        else:
            self.get_logger().warn(f'navigation finished with status={status}')
            self._apply(Event.NAV_FAIL)

    # ------------------------------------------------------------------ timing
    def _on_tick(self) -> None:
        if self.autostart and self._machine.state is State.IDLE and self._machine.mission is None:
            self._assign_next()
            return
        if self._machine.mission is None:
            return

        now = self.now_s()
        if self._machine.state is State.PICKING and self._pick_deadline and now >= self._pick_deadline:
            self._pick_deadline = None
            self.get_logger().info('pick step finished (simulated)')
            self._apply(Event.PICK_OK)
            return

        event = self._machine.tick(now)
        if event is not None:
            self.get_logger().warn(
                f'mission watchdog fired after {self._machine.elapsed(now):.1f} s')
            self._apply(event)
            return

        # retry a dispatch that was pending because Nav2 was not up yet
        if self._machine.state in NAV_STATES and self._goal_handle is None:
            self._dispatch()

    # --------------------------------------------------------------- lifecycle
    def _assign_next(self) -> None:
        if not self._missions:
            return
        if self._index >= len(self._missions):
            if self.loop:
                self._index = 0
            else:
                self._log_summary()
                self.autostart = False
                return

        mission = self._missions[self._index]
        self._index += 1
        self._machine.reset(now=self.now_s())
        self._machine.mission = mission
        self._pick_deadline = None
        self._goal_handle = None
        self.get_logger().info(f'assign mission {mission.mission_id}')
        self._apply(Event.ASSIGN)

    def _failure_note(self) -> str:
        for entry in reversed(self._machine.history):
            if entry['event'] == Event.TIMEOUT.value:
                return 'timeout'
            if entry['event'] == Event.ABORT.value:
                return 'aborted'
            if entry['event'] == Event.NAV_FAIL.value:
                return 'nav_failed'
        return ''

    def _finish(self, state: State) -> None:
        mission = self._machine.mission
        if mission is None:
            return
        result = MissionResult(
            mission_id=mission.mission_id,
            outcome='succeeded' if state is State.DONE else 'aborted',
            duration_s=round(self._machine.elapsed(self.now_s()), 3),
            nav_goals=self._machine.nav_goals,
            nav_failures=self._machine.nav_failures,
            retries_used=self._machine.retries_used,
            note=self._failure_note() if state is not State.DONE else '',
        )
        self._results.append(result)
        if self._recorder is not None:
            self._recorder.write(result)
        self._report_pub.publish(String(data=json.dumps(result.to_dict(), ensure_ascii=False)))
        self.get_logger().info(
            f'mission {result.mission_id}: {result.outcome} in {result.duration_s:.1f} s '
            f'({result.nav_goals} goals, {result.retries_used} retries)')
        self._assign_next()

    def _log_summary(self) -> None:
        if not self._results:
            return
        summary = summarize(self._results)
        self.get_logger().info('session summary: ' + json.dumps(summary, ensure_ascii=False))

    def shutdown(self) -> None:
        self._log_summary()
        if self._recorder is not None:
            self._recorder.close()
            self._recorder = None


def main(argv=None) -> None:
    rclpy.init(args=argv)
    node = MissionServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
