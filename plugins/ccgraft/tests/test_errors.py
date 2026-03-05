"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Tests for the exception hierarchy.
"""

from __future__ import annotations

import pytest

from ccgraft.errors import (
    CcgraftError,
    SessionNotFoundError,
    ManifestError,
    ExportError,
    ImportSessionError,
    RestoreError,
    SessionIdentificationError,
)


def test_all_exceptions_inherit_from_base():
    for exc_cls in (
        SessionNotFoundError,
        ManifestError,
        ExportError,
        ImportSessionError,
        RestoreError,
        SessionIdentificationError,
    ):
        assert issubclass(exc_cls, CcgraftError)


def test_catch_all_with_base():
    with pytest.raises(CcgraftError):
        raise ManifestError("bad manifest")


def test_catch_specific():
    with pytest.raises(ExportError):
        raise ExportError("export failed")


def test_import_session_error_does_not_shadow_builtin():
    assert ImportSessionError is not ImportError
    with pytest.raises(ImportSessionError):
        raise ImportSessionError("ccgraft import failed")
    with pytest.raises(ImportError):
        raise ImportError("real import error")
