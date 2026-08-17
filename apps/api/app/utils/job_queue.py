"""
Automation Studio — background job worker
============================================
Lightweight in-process job queue so firing an automation event doesn't
block the web request that caused it. Before this, `trigger()` ran every
matched workflow's full GraphExecutor synchronously inside the same HTTP
request — a payment confirming, a form submitting, etc. — so the browser
sat waiting for every AI call / webhook / DB query in every matching
workflow to finish before it got a response back. Now `trigger()` just
enqueues the job and returns immediately; the background thread started
here does the actual work.

Read this before assuming it's a Celery-equivalent — it deliberately
isn't one, and pretending otherwise would be worse than not having it:

  - IN-PROCESS ONLY. Jobs live in memory. If this process restarts or
    crashes with jobs still queued, those jobs are gone — no persistence,
    no redelivery. A "must never lose a job" guarantee needs a durable
    broker (Redis/Celery, SQS, etc.) — a real infrastructure decision,
    not something to bolt on silently in a code pass.
  - SINGLE PROCESS ONLY. Run this with more than one worker process
    (`gunicorn -w 4`, multiple dynos, etc.) and each process gets its OWN
    queue and OWN thread — a job enqueued in process A is invisible to
    process B. Fine today for one process (`gunicorn -w 1` or the Flask
    dev server); NOT safe the moment this scales to multiple processes.
    That again needs a shared broker for the same reason.
  - ONE WORKER THREAD = workflows run one at a time, in submission order.
    Still a real improvement over blocking every web request on every
    matching workflow, but it is not parallel execution — a slow
    workflow delays the next queued one, not the web server.

This is a genuine, working improvement for what's actually deployed here
today. It is not a drop-in replacement for a durable multi-process job
system — scaling past one process needs Celery+Redis (or similar), and
that should be a deliberate follow-up with its own hosting decisions,
not something this module quietly pretends to already provide.
"""
import logging
import queue
import threading

_job_queue = queue.Queue()
_app = None
_worker_thread = None
_started = threading.Event()
_log = logging.getLogger(__name__)
_pending_scheduled_ids = set()
_pending_lock = threading.Lock()


def enqueue(event_type, context):
    """Non-blocking — puts the job on the in-memory queue and returns
    immediately. This is what app/utils/automation.py's trigger() now
    calls instead of running the workflow inline."""
    _job_queue.put(("event", event_type, context))


def enqueue_scheduled_workflow(workflow_id):
    """Same queue, same worker thread as enqueue() above — a scheduled
    workflow becoming due runs through the exact same one-at-a-time
    worker as everything else, rather than running directly on the
    scheduler's own tick thread. That matters once more than one
    scheduled workflow is due in the same minute: running them inline on
    the scheduler thread would make a slow workflow delay the next
    tick's due-check for every OTHER scheduled workflow too.
    Guarded against double-queueing: if the worker is still busy with
    this same workflow's PREVIOUS due run when the next minute's tick
    comes around, last_run_at hasn't updated yet, so the naive version of
    this would re-enqueue it again — and again every tick after that —
    stacking up duplicate runs that all fire back-to-back the moment the
    worker catches up. This tracks "already queued, not yet run" per
    workflow so each one is only ever queued once at a time."""
    with _pending_lock:
        if workflow_id in _pending_scheduled_ids:
            return
        _pending_scheduled_ids.add(workflow_id)
    _job_queue.put(("scheduled_workflow", workflow_id, None))


def _worker_loop():
    from app.utils.automation import _execute_trigger, run_scheduled_workflow
    while True:
        kind, a, b = _job_queue.get()
        try:
            with _app.app_context():
                if kind == "scheduled_workflow":
                    run_scheduled_workflow(a)
                else:
                    _execute_trigger(a, b)
        except Exception:
            _log.exception("Background automation job failed (%s: %s)", kind, a)
        finally:
            if kind == "scheduled_workflow":
                with _pending_lock:
                    _pending_scheduled_ids.discard(a)
            _job_queue.task_done()


def start_worker(app):
    """Call once from create_app(). Idempotent — safe if this somehow
    gets called twice (e.g. Flask's debug reloader re-importing modules)
    since a second call would otherwise spawn a second competing worker
    thread pulling from the same queue."""
    global _app, _worker_thread
    if _started.is_set():
        return
    _started.set()
    _app = app
    _worker_thread = threading.Thread(target=_worker_loop, name="automation-worker", daemon=True)
    _worker_thread.start()
    scheduler_thread = threading.Thread(target=_scheduler_loop, name="automation-scheduler", daemon=True)
    scheduler_thread.start()


def _scheduler_loop():
    """Real scheduled/cron-style triggers — a genuine gap before this:
    only event-driven + manual triggers existed, nothing could fire "every
    N minutes/hours". Ticks once a minute, finds active trigger_type
    == "schedule" workflows whose interval has elapsed since
    last_run_at, and enqueues each one individually (not via the normal
    event-broadcast trigger() — see run_scheduled_workflow, which runs
    exactly the one workflow that's actually due, since two scheduled
    workflows can have two different intervals).
    Same in-process/single-thread honesty note as the worker above: this
    lives in this process's memory. Restart the process and the next tick
    just re-evaluates from each workflow's real last_run_at in the
    database, so a missed tick during a restart isn't silently lost
    forever — it fires on the next tick once due — but nothing queued
    survives a mid-flight crash any more durably than the main worker
    queue does.
    """
    import time as _time
    while True:
        _time.sleep(60)
        try:
            with _app.app_context():
                _tick_scheduled_workflows()
        except Exception:
            _log.exception("Scheduler tick failed")


def _tick_scheduled_workflows():
    from datetime import datetime, timedelta
    from app.models.platform import AutomationWorkflow

    due = AutomationWorkflow.query.filter_by(trigger_type="schedule", active=True).all()
    now = datetime.utcnow()
    for wf in due:
        interval_minutes = (wf.trigger_config or {}).get("interval_minutes")
        try:
            interval_minutes = max(1, int(interval_minutes))
        except (TypeError, ValueError):
            interval_minutes = 60  # no/invalid interval configured — default to hourly rather than skip silently forever
        if wf.last_run_at is None or (now - wf.last_run_at) >= timedelta(minutes=interval_minutes):
            enqueue_scheduled_workflow(wf.id)


def queue_depth():
    """How many jobs are currently waiting — real number, not wired into
    any UI yet, but ready for an Executions/monitoring page to surface
    ('3 workflows queued') instead of the request just looking instant
    with no visibility into backlog."""
    return _job_queue.qsize()
