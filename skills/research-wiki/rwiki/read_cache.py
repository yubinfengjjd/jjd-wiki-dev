"""Request-local read snapshots, never persistent validation results."""
from contextlib import contextmanager
from contextvars import ContextVar


_snapshot = ContextVar("rwiki_read_snapshot", default=None)


@contextmanager
def read_session():
    token = _snapshot.set({})
    try:
        yield
    finally:
        _snapshot.reset(token)


def remember(key, build):
    snapshot = _snapshot.get()
    if snapshot is None:
        return build()
    if key not in snapshot:
        snapshot[key] = build()
    return snapshot[key]
