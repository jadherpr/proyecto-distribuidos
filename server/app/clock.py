import threading


class LamportClock:
    def __init__(self) -> None:
        self._value = 0
        self._lock = threading.Lock()

    def restore(self, value: int) -> None:
        with self._lock:
            self._value = max(self._value, value)

    def tick(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def observe(self, received: int) -> int:
        with self._lock:
            self._value = max(self._value, received) + 1
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value
