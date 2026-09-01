from app.greeting import greeting
from app.health import health


def test_greeting() -> None:
    assert greeting("Apollo") in {"Welcome, Apollo.", "Hello, Apollo!"}


def test_health() -> None:
    assert health()["status"] in {"starting", "ok"}
