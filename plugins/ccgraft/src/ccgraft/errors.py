"""Copyright (c) 2026 Achyuth Jayadevan <achyuth@jayadevan.in>
Licensed under the MIT License. See LICENSE file in the project root.

Exception hierarchy for ccgraft.

All ccgraft-specific exceptions derive from CcgraftError, enabling
callers to catch the entire family with a single except clause while
still allowing granular handling when needed.
"""

from __future__ import annotations


class CcgraftError(Exception):
    """Base exception for all ccgraft operations."""


class SessionNotFoundError(CcgraftError):
    """No matching session could be found."""


class ManifestError(CcgraftError):
    """Manifest is missing, malformed, or incompatible."""


class ExportError(CcgraftError):
    """An error occurred during the export pipeline."""


class ImportSessionError(CcgraftError):
    """An error occurred during the import pipeline."""


class RestoreError(CcgraftError):
    """Snapshot restoration failed."""


class SessionIdentificationError(CcgraftError):
    """Could not identify the active session."""
