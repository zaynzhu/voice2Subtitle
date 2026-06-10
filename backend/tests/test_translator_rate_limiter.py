from app.services.translator import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_rate_limiter_keeps_min_interval_between_calls() -> None:
    clock = FakeClock()
    limiter = RateLimiter(
        min_interval_sec=2.0,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
    )

    limiter.wait()
    assert clock.sleeps == []

    clock.now += 0.5
    limiter.wait()
    assert clock.sleeps == [1.5]

    clock.now += 2.1
    limiter.wait()
    assert clock.sleeps == [1.5]
