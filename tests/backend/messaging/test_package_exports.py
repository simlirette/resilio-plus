"""The package root is a re-export shim — pin it so a typo cannot slip in.

`__all__` entries are only resolved on `from app.messaging import *`, which no
production code does, so a misspelled name would otherwise sit undetected until
someone tried it.
"""
from __future__ import annotations

import app.messaging as messaging


def test_every_exported_name_resolves() -> None:
    missing = [name for name in messaging.__all__ if not hasattr(messaging, name)]
    assert missing == []


def test_star_import_binds_exactly_the_declared_names() -> None:
    namespace: dict[str, object] = {}
    exec("from app.messaging import *", namespace)  # noqa: S102 — that is the point
    bound = {name for name in namespace if not name.startswith("__")}
    assert bound == set(messaging.__all__)


def test_all_is_sorted_and_unique() -> None:
    assert len(set(messaging.__all__)) == len(messaging.__all__)
    assert list(messaging.__all__) == sorted(messaging.__all__)


def test_the_public_surface_covers_each_submodule() -> None:
    """A new module added to the package should be reachable from the root."""
    for name in (
        "MessagingGateway",
        "NotificationService",
        "ApprovalService",
        "chunk_message",
        "render_week",
        "create_approval",
        "parse_callback",
    ):
        assert name in messaging.__all__
