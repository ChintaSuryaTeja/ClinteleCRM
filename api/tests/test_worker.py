from app.worker import ping


def test_ping_task_runs():
    # apply() runs the task in this process, so the test needs no Redis.
    assert ping.apply().get() == "pong"
