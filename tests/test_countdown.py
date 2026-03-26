import time
from queue import Queue

from macro_recorder.app.countdown import CountdownRunner


def test_countdown_emits_done():
    q = Queue()
    c = CountdownRunner(q)
    c.start(1, "play")
    time.sleep(1.2)
    events = []
    while not q.empty():
        events.append(q.get_nowait().type)
    assert "play_tick" in events
    assert "play_done" in events
