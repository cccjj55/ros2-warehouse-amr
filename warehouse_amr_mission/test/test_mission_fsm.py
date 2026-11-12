"""Unit tests for the mission state machine (no ROS, no simulator)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from warehouse_amr_mission.mission_fsm import (  # noqa: E402
    NAV_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    Event,
    InvalidTransition,
    Mission,
    MissionMachine,
    State,
)


def make_machine(**kwargs) -> MissionMachine:
    machine = MissionMachine(**kwargs)
    machine.mission = Mission('m1', (1.0, 1.0, 0.0), (3.0, 2.0, 1.57))
    return machine


def test_happy_path_reaches_done():
    machine = make_machine()
    assert machine.step(Event.ASSIGN) is State.GO_TO_PICK
    assert machine.step(Event.NAV_OK) is State.PICKING
    assert machine.step(Event.PICK_OK) is State.GO_TO_DROP
    assert machine.step(Event.NAV_OK) is State.DONE
    assert machine.retries_used == 0
    assert machine.nav_failures == 0


def test_nav_failure_retries_up_to_budget_then_fails():
    machine = make_machine(max_nav_retries=2)
    machine.step(Event.ASSIGN)

    assert machine.step(Event.NAV_FAIL) is State.GO_TO_PICK
    assert machine.step(Event.NAV_FAIL) is State.GO_TO_PICK
    assert machine.step(Event.NAV_FAIL) is State.FAILED
    assert machine.nav_failures == 3
    assert machine.retries_used == 2


def test_zero_retry_budget_fails_on_first_failure():
    machine = make_machine(max_nav_retries=0)
    machine.step(Event.ASSIGN)
    assert machine.step(Event.NAV_FAIL) is State.FAILED
    assert machine.retries_used == 0


def test_timeout_behaves_like_a_failure_on_the_leg():
    machine = make_machine(max_nav_retries=1)
    machine.step(Event.ASSIGN)
    assert machine.step(Event.TIMEOUT) is State.GO_TO_PICK
    assert machine.step(Event.TIMEOUT) is State.FAILED


def test_timeout_while_picking_is_terminal():
    machine = make_machine()
    machine.step(Event.ASSIGN)
    machine.step(Event.NAV_OK)
    assert machine.step(Event.TIMEOUT) is State.FAILED


def test_pick_failure_returns_to_pick_leg():
    machine = make_machine(max_nav_retries=2)
    machine.step(Event.ASSIGN)
    machine.step(Event.NAV_OK)
    assert machine.step(Event.PICK_FAIL) is State.GO_TO_PICK
    assert machine.nav_failures == 1


def test_abort_is_immediate_from_any_active_state():
    for setup in (
        [Event.ASSIGN],
        [Event.ASSIGN, Event.NAV_OK],
        [Event.ASSIGN, Event.NAV_OK, Event.PICK_OK],
    ):
        machine = make_machine()
        for event in setup:
            machine.step(event)
        assert machine.step(Event.ABORT) is State.FAILED


def test_abort_without_active_mission_is_a_noop():
    machine = make_machine()
    assert machine.step(Event.ABORT) is State.IDLE


def test_undefined_event_raises_instead_of_being_ignored():
    machine = make_machine()
    with pytest.raises(InvalidTransition):
        machine.step(Event.NAV_OK)          # NAV_OK is meaningless in IDLE
    machine.step(Event.ASSIGN)
    with pytest.raises(InvalidTransition):
        machine.step(Event.PICK_OK)         # PICKING not reached yet


def test_reset_returns_to_idle_and_clears_counters():
    machine = make_machine()
    machine.step(Event.ASSIGN)
    machine.step(Event.NAV_FAIL)
    machine.reset()
    assert machine.state is State.IDLE
    assert machine.mission is None
    assert machine.nav_failures == 0
    assert machine.history == []


def test_tick_returns_timeout_only_after_budget():
    machine = make_machine(mission_timeout_s=10.0)
    machine.step(Event.ASSIGN)
    assert machine.tick(now=machine.started_at + 5.0) is None
    assert machine.tick(now=machine.started_at + 10.5) is Event.TIMEOUT


def test_tick_is_silent_once_terminal():
    machine = make_machine(mission_timeout_s=1.0)
    machine.step(Event.ASSIGN)
    machine.step(Event.ABORT)
    assert machine.tick(now=machine.started_at + 100.0) is None


def test_history_records_every_transition():
    machine = make_machine()
    machine.step(Event.ASSIGN)
    machine.step(Event.NAV_OK)
    assert [entry['to'] for entry in machine.history] == ['GO_TO_PICK', 'PICKING']
    assert machine.history[1]['event'] == 'NAV_OK'


def test_every_active_state_can_reach_a_terminal_state():
    """Reachability guard: no state may be a dead end."""
    active = [State.IDLE] + [s for s in State if s not in TERMINAL_STATES]
    for start in active:
        frontier, seen = [start], {start}
        while frontier:
            state = frontier.pop()
            if state in TERMINAL_STATES:
                break
            for (src, _event), transition in TRANSITIONS.items():
                if src is state and transition.next_state not in seen:
                    seen.add(transition.next_state)
                    frontier.append(transition.next_state)
        else:
            continue
        assert seen & TERMINAL_STATES, f'{start} cannot reach a terminal state'


def test_nav_states_and_terminal_sets_are_consistent():
    assert NAV_STATES == {State.GO_TO_PICK, State.GO_TO_DROP}
    assert TERMINAL_STATES == {State.DONE, State.FAILED}


def test_mission_parsing_and_validation():
    mission = Mission.from_dict({'id': 'a', 'pick': [1, 2, 0.5], 'drop': [3, 4, -1.0]})
    assert mission.pick == (1.0, 2.0, 0.5)
    assert mission.mission_id == 'a'
    with pytest.raises(ValueError):
        Mission.from_dict({'id': 'b', 'pick': [1, 2], 'drop': [3, 4, 0]})


def test_invalid_construction_arguments_rejected():
    with pytest.raises(ValueError):
        MissionMachine(max_nav_retries=-1)
    with pytest.raises(ValueError):
        MissionMachine(mission_timeout_s=0.0)
