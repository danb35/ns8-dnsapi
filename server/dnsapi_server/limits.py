#
# Copyright (C) 2026 Dan Brown
# SPDX-License-Identifier: GPL-3.0-or-later
#
# In-memory counters: per-key rate limits and the failed-authentication
# throttle per source address (DESIGN.md, Security). They reset when the
# service restarts, which is acceptable for limits measured in a minute.

import math
import threading
import time
from collections import deque


class SlidingWindow:
    """At most `limit` events per `window` seconds for each name."""

    def __init__(self, window=60.0, clock=time.monotonic):
        self.window = window
        self.clock = clock
        self.events = {}
        self.lock = threading.Lock()

    def _trim(self, name, now):
        queue = self.events.get(name)
        if queue is None:
            return None
        while queue and queue[0] <= now - self.window:
            queue.popleft()
        if not queue:
            del self.events[name]
            return None
        return queue

    def retry_after(self, name, limit):
        """Seconds to wait before an event for `name` is allowed; 0 when allowed now."""
        with self.lock:
            now = self.clock()
            queue = self._trim(name, now)
            if limit <= 0:
                return 0
            if queue is None or len(queue) < limit:
                return 0
            return max(1, math.ceil(queue[0] + self.window - now))

    def hit(self, name, limit):
        """Record an event unless the limit is reached. Return the seconds to wait (0 = recorded)."""
        with self.lock:
            now = self.clock()
            queue = self._trim(name, now)
            if limit > 0 and queue is not None and len(queue) >= limit:
                return max(1, math.ceil(queue[0] + self.window - now))
            self.events.setdefault(name, deque()).append(now)
            return 0

    def clear(self, name):
        with self.lock:
            self.events.pop(name, None)
