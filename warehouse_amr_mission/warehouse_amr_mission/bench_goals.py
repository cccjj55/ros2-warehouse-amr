"""Random-goal navigation benchmark.

Sends ``n_goals`` uniform random goals inside a rectangular free-space region,
times each one, and writes a reproducible JSON artifact plus a Markdown table
that ``scripts/render_bench_table.py`` can splice into the README.

    ros2 run warehouse_amr_mission bench_goals --ros-args \
        -p n_goals:=25 -p out_json:=docs/benchmarks/latest.json

Exit code is 0 when the success rate reaches ``success_threshold`` (default
0.9), so CI can gate on it when a headless simulator is available.
"""

from __future__ import annotations

import json
import math
import random
import sys
from typing import Optional

import rclpy
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node

from warehouse_amr_mission.metrics import MissionResult, render_table, summarize, write_summary
from warehouse_amr_mission.mission_server import pose_stamped


class BenchGoals(Node):
    def __init__(self) -> None:
        super().__init__('bench_goals')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('n_goals', 20)
        self.declare_parameter('x_min', 0.6)
        self.declare_parameter('x_max', 9.4)
        self.declare_parameter('y_min', 0.6)
        self.declare_parameter('y_max', 5.4)
        self.declare_parameter('goal_timeout_s', 60.0)
        self.declare_parameter('seed', 7)
        self.declare_parameter('out_json', '')
        self.declare_parameter('success_threshold', 0.9)

        self.frame_id = self.get_parameter('frame_id').value
        self.n_goals = int(self.get_parameter('n_goals').value)
        self.goal_timeout_s = float(self.get_parameter('goal_timeout_s').value)
        self.out_json = self.get_parameter('out_json').value
        self.success_threshold = float(self.get_parameter('success_threshold').value)

        rng = random.Random(int(self.get_parameter('seed').value))
        bounds = (
            float(self.get_parameter('x_min').value),
            float(self.get_parameter('x_max').value),
            float(self.get_parameter('y_min').value),
            float(self.get_parameter('y_max').value),
        )
        x_min, x_max, y_min, y_max = bounds
        self.goals = [
            (rng.uniform(x_min, x_max), rng.uniform(y_min, y_max), rng.uniform(-math.pi, math.pi))
            for _ in range(self.n_goals)
        ]

        self.results = []
        self.finished = False
        self.exit_code = 0
        self._index = -1
        self._goal_started = 0.0
        self._server_waited = 0.0
        self._goal_handle = None
        self._active = False

        self._client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._timer = self.create_timer(0.5, self._on_tick)

    # ------------------------------------------------------------------ timing
    def now_s(self) -> float:
        return self.get_clock().now().nanoseconds / 1e9

    def _on_tick(self) -> None:
        if self.finished:
            return
        if not self._client.server_is_ready():
            self._server_waited += 0.5
            if self._server_waited > 30.0:
                self.get_logger().error('navigate_to_pose action server never appeared')
                self._finalize()
            return

        if not self._active:
            self._send_next()
            return

        if self.now_s() - self._goal_started > self.goal_timeout_s:
            self.get_logger().warn(f'goal {self._index} timed out, cancelling')
            if self._goal_handle is not None:
                self._goal_handle.cancel_goal_async()
            self._record('timeout', note='goal_timeout')

    # ---------------------------------------------------------------- dispatch
    def _send_next(self) -> None:
        self._index += 1
        if self._index >= len(self.goals):
            self._finalize()
            return

        goal = NavigateToPose.Goal()
        goal.pose = pose_stamped(self.frame_id, self.goals[self._index], self.get_clock().now().to_msg())
        self._goal_started = self.now_s()
        self._active = True
        self._goal_handle = None
        self._client.send_goal_async(goal).add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future) -> None:
        handle = future.result()
        if handle is None or not handle.accepted:
            self.get_logger().warn(f'goal {self._index} rejected')
            self._record('aborted', note='goal_rejected')
            return
        self._goal_handle = handle
        handle.get_result_async().add_done_callback(self._on_result)

    def _on_result(self, future) -> None:
        wrapped = future.result()
        status = wrapped.status if wrapped is not None else GoalStatus.STATUS_ABORTED
        if status == GoalStatus.STATUS_SUCCEEDED:
            self._record('succeeded')
        elif status == GoalStatus.STATUS_CANCELED:
            self._record('timeout', note='cancelled')
        else:
            self._record('aborted', note=f'status_{status}')

    # ---------------------------------------------------------------- records
    def _record(self, outcome: str, note: str = '') -> None:
        if not self._active:
            return
        self._active = False
        self._goal_handle = None
        result = MissionResult(
            mission_id=f'goal_{self._index:03d}',
            outcome=outcome,
            duration_s=round(self.now_s() - self._goal_started, 3),
            nav_goals=1,
            nav_failures=0 if outcome == 'succeeded' else 1,
            retries_used=0,
            note=note,
        )
        self.results.append(result)
        self.get_logger().info(
            f'{result.mission_id}: {outcome} in {result.duration_s:.1f} s {("(" + note + ")") if note else ""}')
        self._send_next()

    def _finalize(self) -> None:
        if self.finished:
            return
        self.finished = True
        self._timer.cancel()

        summary = summarize(self.results)
        meta = {'sim': 'gazebo classic / nav2 humble', 'goals': self.n_goals}
        if self.out_json:
            write_summary(self.out_json, self.results, meta=meta)
            self.get_logger().info(f'wrote {self.out_json}')
        self.get_logger().info('summary: ' + json.dumps(summary, ensure_ascii=False))
        self.get_logger().info('\n' + render_table(summary, meta))

        self.exit_code = 0 if summary['success_rate'] >= self.success_threshold else 1


def main(argv=None) -> int:
    rclpy.init(args=argv)
    node = BenchGoals()
    exit_code = 0
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
        exit_code = node.exit_code
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
