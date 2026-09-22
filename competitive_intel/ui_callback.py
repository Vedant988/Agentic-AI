"""
competitive_intel/ui_callback.py
---------------------------------
Thread-safe event bus that agents write to and the Streamlit UI reads from.

Agents emit structured events via `emit(type, agent, message, data)`.
The UI drains the queue with `drain()` inside a polling loop.

Event types:
  "plan"      — orchestrator JSON plan  (data = dict)
  "step"      — step started / status   (data = {step, status, detail})
  "tool_call" — a tool invocation       (data = {tool, args_preview})
  "tool_ok"   — tool succeeded          (data = {result_preview})
  "tool_fail" — tool failed             (data = {error, recovery})
  "tool_recovery" — recovery attempt    (data = {query})
  "findings"  — agent findings preview  (data = {preview})
  "validate"  — pydantic validation     (data = {valid, errors})
  "fanin"     — fan-in completed        (data = {})
  "synthesis_start" — synthesis begins  (data = {})
  "synthesis_token" — one streamed tok  (data = {token})
  "synthesis_done"  — synthesis done    (data = {chars})
  "done"      — full pipeline done      (data = {elapsed, sector, competitors})
  "error"     — unhandled error         (data = {error})
"""

import queue
import threading

_queue: queue.Queue = queue.Queue()
_active: bool = False
_lock = threading.Lock()


def activate():
    """Call this from Streamlit before starting the graph."""
    global _active
    with _lock:
        # drain any stale events
        while not _queue.empty():
            try:
                _queue.get_nowait()
            except queue.Empty:
                break
        _active = True


def deactivate():
    global _active
    with _lock:
        _active = False


def is_active() -> bool:
    with _lock:
        return _active


def emit(event_type: str, agent: str, message: str, data: dict = None):
    """Called by agent code to push an event to the UI queue."""
    if not is_active():
        return
    _queue.put({
        "type": event_type,
        "agent": agent,
        "message": message,
        "data": data or {},
    })


def drain(timeout: float = 0.05) -> list[dict]:
    """Drain all currently queued events (non-blocking). Used by Streamlit."""
    events = []
    while True:
        try:
            events.append(_queue.get_nowait())
        except queue.Empty:
            break
    return events
