"""Tests for execution trace."""

from app.agent.trace import TraceRecorder


def test_trace_records_steps():
    trace = TraceRecorder()
    trace.record(action="CALL_CAPABILITY", capability="cap1", status="success")
    trace.record(action="FINAL", status="complete")
    assert len(trace.steps) == 2
    assert trace.steps[0].step_number == 1
    assert trace.steps[1].step_number == 2


def test_trace_timer():
    trace = TraceRecorder()
    trace.start_timer()
    import time
    time.sleep(0.05)  # 50ms — Windows has coarser timer resolution
    latency = trace.stop_timer()
    assert latency > 0


def test_trace_no_cot():
    """Trace should contain short rationale, never chain-of-thought."""
    trace = TraceRecorder()
    trace.record(
        action="CALL_CAPABILITY",
        capability="interpret_scene",
        rationale="Scene interpretation needed.",
    )
    step = trace.steps[0]
    # rationale should be short and observable
    assert len(step.rationale) < 200
    assert "chain" not in step.rationale.lower()
    assert "thought" not in step.rationale.lower()


def test_trace_to_dicts():
    trace = TraceRecorder()
    trace.record(action="CALL_CAPABILITY", capability="cap1", status="success")
    dicts = trace.to_dicts()
    assert len(dicts) == 1
    assert dicts[0]["action"] == "CALL_CAPABILITY"
    assert "timestamp" in dicts[0]


def test_trace_includes_latency():
    trace = TraceRecorder()
    trace.record(
        action="CALL_CAPABILITY", capability="cap1",
        status="success", latency_s=2.5
    )
    assert trace.steps[0].latency_s == 2.5


def test_trace_includes_confidence():
    trace = TraceRecorder()
    trace.record(
        action="CALL_CAPABILITY", capability="cap1",
        status="success", confidence=0.87
    )
    assert trace.steps[0].confidence == 0.87
