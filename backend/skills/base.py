"""Skill Base Class.

All skills in Git Phantom Scope inherit from SkillBase.
Skills are modular, self-contained units of functionality
that can be composed into pipelines.

Adapted from phantom-neural-cortex skill system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SkillStatus(str, Enum):
    """Skill execution status."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class SkillMetadata:
    """Metadata for a skill definition."""

    name: str
    version: str
    description: str
    author: str = "LEEI1337"
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # Required dependencies


@dataclass
class SkillContext:
    """Context passed to skill execution.

    Contains all the data a skill needs to operate.
    PRIVACY: No PII should be stored in context beyond
    what's needed for the current operation.
    """

    session_id: str
    profile_data: dict[str, Any] = field(default_factory=dict)
    scoring_data: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    byok_keys: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Result of a skill execution."""

    status: SkillStatus
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def is_success(self) -> bool:
        return self.status == SkillStatus.SUCCESS


class SkillBase(ABC):
    """Abstract base class for all skills."""

    metadata: SkillMetadata

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill with the given context.

        Args:
            context: Skill execution context with profile and config data

        Returns:
            SkillResult with status and output data
        """
        ...

    async def validate(self, context: SkillContext) -> bool:
        """Validate that the skill can execute with the given context.

        Override this to add custom validation logic.
        Default implementation returns True.
        """
        return True

    def __repr__(self) -> str:
        return f"<Skill: {self.metadata.name} v{self.metadata.version}>"
