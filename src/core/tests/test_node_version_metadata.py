"""Regression guards for per-node version metadata (UI change detection).

Every concrete node class registered in NodeTypeRegistry MUST declare
`_version` / `_updated_at` in its own class body (inherited base defaults
are rejected). Format is enforced via SemVer + ISO 8601 regex.

Rationale: UI developers consume `NodeTypeSchema.version` / `updated_at` to
detect changed nodes between releases without consulting CHANGELOG / git log.
A silently inherited base default would defeat that purpose, so we require
explicit per-class declarations.
"""

import re

import pytest

from programgarden_core.registry import NodeTypeRegistry


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CHANGE_NOTE_MAX_LEN = 120


def _registered_node_classes():
    registry = NodeTypeRegistry()
    return [(name, registry.get(name)) for name in registry.list_types()]


class TestNodeVersionMetadata:
    """Per-node version metadata regression guards."""

    def test_every_node_declares_version(self):
        for name, cls in _registered_node_classes():
            assert "_version" in cls.__dict__, (
                f"{name} must declare `_version` in its own class body. "
                'Add `_version: ClassVar[str] = "1.0.0"` (or higher).'
            )

    def test_every_node_declares_updated_at(self):
        for name, cls in _registered_node_classes():
            assert "_updated_at" in cls.__dict__, (
                f"{name} must declare `_updated_at` in its own class body. "
                'Add `_updated_at: ClassVar[str] = "YYYY-MM-DD"`.'
            )

    def test_version_is_valid_semver(self):
        for name, cls in _registered_node_classes():
            value = getattr(cls, "_version")
            assert isinstance(value, str), (
                f"{name}._version must be str, got {type(value).__name__}"
            )
            assert SEMVER_RE.match(value), (
                f"{name}._version = {value!r} is not valid SemVer "
                "(major.minor.patch, digits only)"
            )

    def test_updated_at_is_iso_date(self):
        for name, cls in _registered_node_classes():
            value = getattr(cls, "_updated_at")
            assert isinstance(value, str), (
                f"{name}._updated_at must be str, got {type(value).__name__}"
            )
            assert ISO_DATE_RE.match(value), (
                f"{name}._updated_at = {value!r} is not ISO 8601 (YYYY-MM-DD)"
            )

    def test_change_note_is_str_or_none(self):
        for name, cls in _registered_node_classes():
            note = getattr(cls, "_change_note", None)
            assert note is None or isinstance(note, str), (
                f"{name}._change_note must be Optional[str], "
                f"got {type(note).__name__}"
            )
            if isinstance(note, str):
                assert len(note) <= CHANGE_NOTE_MAX_LEN, (
                    f"{name}._change_note too long ({len(note)} > "
                    f"{CHANGE_NOTE_MAX_LEN}). Keep under {CHANGE_NOTE_MAX_LEN} "
                    "chars for UI tooltip rendering."
                )

    def test_schema_exposes_version_fields(self):
        registry = NodeTypeRegistry()
        schema = registry.get_schema("StartNode")
        assert schema is not None
        dumped = schema.model_dump()
        for field in ("version", "updated_at", "change_note"):
            assert field in dumped, f"NodeTypeSchema missing '{field}' field"
        assert SEMVER_RE.match(dumped["version"])
        assert ISO_DATE_RE.match(dumped["updated_at"])

    def test_list_schemas_includes_version_fields(self):
        """All schemas returned by list_schemas() must expose the version trio."""
        registry = NodeTypeRegistry()
        schemas = registry.list_schemas()
        assert len(schemas) > 0
        for schema in schemas:
            dumped = schema.model_dump()
            assert "version" in dumped, (
                f"schema for {schema.node_type} missing 'version'"
            )
            assert SEMVER_RE.match(dumped["version"]), (
                f"{schema.node_type}.version = {dumped['version']!r} invalid"
            )
            assert ISO_DATE_RE.match(dumped["updated_at"]), (
                f"{schema.node_type}.updated_at = {dumped['updated_at']!r} invalid"
            )
