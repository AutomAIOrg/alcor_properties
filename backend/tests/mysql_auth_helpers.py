"""Opt-in MySQL tests create and drop only their own randomly named database."""

import os
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from infrastructure.database.base import Base


@contextmanager
def isolated_mysql():
    raw = os.getenv("AUTH_TEST_MYSQL_URL")
    if not raw:
        pytest.skip("Set AUTH_TEST_MYSQL_URL to a disposable MySQL server")
    url = make_url(raw)
    name = "alcor_auth_test_" + uuid.uuid4().hex
    admin = create_engine(url.set(database=None), isolation_level="AUTOCOMMIT")
    engine = None
    with admin.connect() as db:
        db.execute(text(f"CREATE DATABASE `{name}`"))
    try:
        engine = create_engine(url.set(database=name), pool_size=16, max_overflow=4)
        Base.metadata.create_all(engine)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as db:
            db.execute(text(f"DROP DATABASE `{name}`"))
        admin.dispose()
