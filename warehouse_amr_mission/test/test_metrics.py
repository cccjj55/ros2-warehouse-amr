"""Unit tests for metric aggregation and README table rendering."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from warehouse_amr_mission.metrics import (  # noqa: E402
    JsonlRecorder,
    MissionResult,
    load_jsonl,
    percentile,
    render_readme_block,
    render_table,
    summarize,
    write_summary,
)


def results():
    return [
        MissionResult('a', 'succeeded', 10.0, nav_goals=2),
        MissionResult('b', 'succeeded', 20.0, nav_goals=3, retries_used=1),
        MissionResult('c', 'succeeded', 30.0, nav_goals=2),
        MissionResult('d', 'aborted', 40.0, nav_goals=4, retries_used=2, note='nav_failed'),
    ]


def test_percentile_edges_and_interpolation():
    assert percentile([], 50) == 0.0
    assert percentile([5.0], 95) == 5.0
    assert percentile([0.0, 10.0], 50) == 5.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 100) == 4.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0) == 1.0


def test_summarize_counts_rate_and_latency():
    summary = summarize(results())
    assert summary['missions'] == 4
    assert summary['succeeded'] == 3
    assert summary['failed'] == 1
    assert summary['success_rate'] == 0.75
    assert summary['duration_mean_s'] == 25.0
    assert summary['duration_p50_s'] == 25.0
    assert summary['nav_goals_mean'] == 2.75
    assert summary['retries_total'] == 3
    assert summary['failure_reasons'] == {'nav_failed': 1}


def test_summarize_of_empty_input_is_safe():
    summary = summarize([])
    assert summary['missions'] == 0
    assert summary['success_rate'] == 0.0
    assert summary['duration_p95_s'] == 0.0


def test_jsonl_recorder_roundtrip(tmp_path):
    path = tmp_path / 'nested' / 'missions.jsonl'
    with JsonlRecorder(str(path)) as recorder:
        recorder.write(results()[0])
        recorder.write(results()[3].to_dict())

    loaded = load_jsonl(str(path))
    assert [row.mission_id for row in loaded] == ['a', 'd']
    assert loaded[1].note == 'nav_failed'
    raw = path.read_text(encoding='utf-8').splitlines()
    assert json.loads(raw[0])['outcome'] == 'succeeded'


def test_write_summary_artifact_shape(tmp_path):
    path = tmp_path / 'latest.json'
    payload = write_summary(str(path), results(), meta={'sim': 'gazebo'})
    assert payload['summary']['success_rate'] == 0.75
    assert payload['meta']['sim'] == 'gazebo'
    assert len(payload['rows']) == 4
    on_disk = json.loads(path.read_text(encoding='utf-8'))
    assert on_disk['summary']['missions'] == 4


def test_render_table_contains_the_numbers():
    table = render_table(summarize(results()), {'git_sha': 'abcdef1234', 'timestamp': '2026-01-01'})
    assert '75.0 % (3/4)' in table
    assert 'abcdef12' in table
    assert table.startswith('| 指标 / metric | 值 / value |')


def test_render_readme_block_has_markers():
    block = render_readme_block(summarize(results()))
    assert block.startswith('<!-- BENCH:START -->')
    assert block.rstrip().endswith('<!-- BENCH:END -->')
