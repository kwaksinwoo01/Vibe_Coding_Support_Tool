"""Development SDK for the ReNamer project.

Scope is intentionally limited to ReNamer. The Word Editor project owns and
implements its own SDK tree independently.

This package is repository tooling. Product runtime code must not depend on it.
"""

SDK_RESPONSIBILITIES = {
    "core_sdk": "common execution contracts and foundation types only",
    "build_sdk": "build and release-source inspection",
    "test_sdk": "independent oracle, fixtures, and scenario matrices",
    "sdk_suite": "toolchain composition and orchestration",
    "observability_sdk": "diagnostic events and execution visibility",
    "validation_sdk": "contract and invariant validation",
    "model_sdk": "structured ReNamer SDK data models",
    "integration_sdk": "repository, filesystem, process, and OS adapters",
    "migration_sdk": "version-to-version migration planning",
    "domain_sdk": "pure ReNamer business rules",
}

OUT_OF_SCOPE = ("word_editor_sdk",)

__all__ = list(SDK_RESPONSIBILITIES)
