from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def commit_or_rollback(session: Session) -> Iterator[None]:
    try:
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise
