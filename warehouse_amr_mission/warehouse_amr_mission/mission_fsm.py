"""Deterministic mission state machine for the warehouse AMR.

Deliberately free of ROS imports: the whole decision layer runs under plain
pytest in CI (``test/test_mission_fsm.py``), including the retry and timeout
branches. That is what makes "the robot recovers from a failed goal" a testable
claim instead of a story about the one time it worked in the simulator.

State graph (see docs/ARCHITECTURE.md for the rendered version)::

    IDLE --ASSIGN--> GO_TO_PICK --NAV_OK--> PICKING --PICK_OK--> GO_TO_DROP --NAV_OK--> DONE
                        ^  |                   |                    ^  |
                   retry|  | ABORT        FAIL/PICK_FAIL  retry    |  | ABORT
                        +--+                   |                    +--+
                                               v
                                            FAILED --RESET--> IDLE
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class State(str, enum.Enum):
    IDLE = 'IDLE'
    GO_TO_PICK = 'GO_TO_PICK'
    PICKING = 'PICKING'
    GO_TO_DROP = 'GO_TO_DROP'
    DONE = 'DONE'
    FAILED = 'FAILED'


class Event(str, enum.Enum):
    ASSIGN = 'ASSIGN'
    NAV_OK = 'NAV_OK'
    NAV_FAIL = 'NAV_FAIL'
    PICK_OK = 'PICK_OK'
    PICK_FAIL = 'PICK_FAIL'
    TIMEOUT = 'TIMEOUT'
    ABORT = 'ABORT'
    RESET = 'RESET'


TERMINAL_STATES = frozenset({State.DONE, State.FAILED})
NAV_STATES = frozenset({State.GO_TO_PICK, State.GO_TO_DROP})


class InvalidTransition(RuntimeError):
    """Raised when an event is not defined for the current state.

    Loud failure on purpose: silently ignoring an unexpected event is how
    robots end up parked in a corner waiting for a goal nobody will send.
    """

    def __init__(self, state: State, event: Event) -> None:
        super().__init__(f'no transition defined for {event.value} in {state.value}')
        self.state = state
        self.event = event


@dataclass(frozen=True)
class Transition:
    next_state: State
    retry: bool = False
    note: str = ''


TRANSITIONS: Dict[Tuple[State, Event], Transition] = {
    (State.IDLE, Event.ASSIGN): Transition(State.GO_TO_PICK, note='dispatch first leg'),
    (State.IDLE, Event.ABORT): Transition(State.IDLE, note='no active mission: no-op'),
    (State.GO_TO_PICK, Event.NAV_OK): Transition(State.PICKING),
    (State.GO_TO_PICK, Event.NAV_FAIL): Transition(State.GO_TO_PICK, retry=True),
    (State.GO_TO_PICK, Event.TIMEOUT): Transition(State.GO_TO_PICK, retry=True),
    (State.GO_TO_PICK, Event.ABORT): Transition(State.FAILED),
    (State.PICKING, Event.PICK_OK): Transition(State.GO_TO_DROP),
    (State.PICKING, Event.PICK_FAIL): Transition(State.GO_TO_PICK, retry=True),
    (State.PICKING, Event.TIMEOUT): Transition(State.FAILED),
    (State.PICKING, Event.ABORT): Transition(State.FAILED),
    (State.GO_TO_DROP, Event.NAV_OK): Transition(State.DONE),
    (State.GO_TO_DROP, Event.NAV_FAIL): Transition(State.GO_TO_DROP, retry=True),
    (State.GO_TO_DROP, Event.TIMEOUT): Transition(State.GO_TO_DROP, retry=True),
    (State.GO_TO_DROP, Event.ABORT): Transition(State.FAILED),
    (State.DONE, Event.RESET): Transition(State.IDLE),
    (State.FAILED, Event.RESET): Transition(State.IDLE),
}


@dataclass(frozen=True)
class Mission:
    """One pick-and-drop job. Poses are ``(x, y, yaw)`` in the map frame."""

    mission_id: str
    pick: Tuple[float, float, float]
    drop: Tuple[float, float, float]
    dock: Tuple[float, float, float] = (0.75, 4.75, 1.57)

    @classmethod
    def from_dict(cls, raw: Dict) -> 'Mission':
        def pose(key: str) -> Tuple[float, float, float]:
            value = raw[key]
            if len(value) != 3:
                raise ValueError(f'{key} must be [x, y, yaw], got {value!r}')
            x, y, yaw = (float(v) for v in value)
            return (x, y, yaw)

        return cls(
            mission_id=str(raw['id']),
            pick=pose('pick'),
            drop=pose('drop'),
            dock=pose('dock') if 'dock' in raw else cls.dock,
        )


@dataclass
class MissionMachine:
    """Transition table + retry / timeout policy.

    ``max_nav_retries`` is the number of *extra* attempts allowed per leg; a
    mission therefore issues at most ``1 + max_nav_retries`` goals per leg.
    """

    max_nav_retries: int = 2
    mission_timeout_s: float = 60.0
    state: State = State.IDLE
    mission: Optional[Mission] = None
    nav_failures: int = 0
    retries_used: int = 0
    nav_goals: int = 0
    started_at: float = 0.0
    state_entered: float = 0.0
    history: List[Dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.max_nav_retries < 0:
            raise ValueError('max_nav_retries must be >= 0')
        if self.mission_timeout_s <= 0:
            raise ValueError('mission_timeout_s must be > 0')
        now = time.monotonic()
        self.started_at = now
        self.state_entered = now

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _now(now: Optional[float]) -> float:
        return time.monotonic() if now is None else now

    def can(self, event: Event) -> bool:
        return (self.state, event) in TRANSITIONS

    def elapsed(self, now: Optional[float] = None) -> float:
        return max(0.0, self._now(now) - self.started_at)

    def mark_goal_sent(self) -> None:
        """Called by the ROS layer when a NavigateToPose goal is dispatched."""
        self.nav_goals += 1

    def tick(self, now: Optional[float] = None) -> Optional[Event]:
        """Watchdog: returns the event the machine *should* receive, if any."""
        if self.state in TERMINAL_STATES:
            return None
        if self.elapsed(now) > self.mission_timeout_s:
            return Event.TIMEOUT
        return None

    # ------------------------------------------------------------ transition
    def step(self, event: Event, now: Optional[float] = None) -> State:
        now = self._now(now)
        transition = TRANSITIONS.get((self.state, event))
        if transition is None:
            raise InvalidTransition(self.state, event)

        nxt = transition.next_state
        if transition.retry:
            self.nav_failures += 1
            if self.nav_failures > self.max_nav_retries:
                nxt = State.FAILED
            else:
                self.retries_used += 1

        self.history.append({
            't': round(now - self.started_at, 3),
            'event': event.value,
            'from': self.state.value,
            'to': nxt.value,
            'retry': transition.retry,
        })
        if nxt is not self.state:
            self.state = nxt
            self.state_entered = now
        return self.state

    def reset(self, now: Optional[float] = None) -> None:
        now = self._now(now)
        self.state = State.IDLE
        self.mission = None
        self.nav_failures = 0
        self.retries_used = 0
        self.nav_goals = 0
        self.started_at = now
        self.state_entered = now
        self.history.clear()

    def snapshot(self, now: Optional[float] = None) -> Dict:
        return {
            'state': self.state.value,
            'mission_id': self.mission.mission_id if self.mission else None,
            'nav_goals': self.nav_goals,
            'nav_failures': self.nav_failures,
            'retries_used': self.retries_used,
            'elapsed_s': round(self.elapsed(now), 3),
        }
