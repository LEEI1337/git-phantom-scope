"""Skill Registry - Auto-Discovery and Management.

Discovers, registers, and manages all available skills.
Skills can be registered manually or discovered automatically
from the skills directory.
"""

from __future__ import annotations

from typing import Optional

from app.logging_config import get_logger
from skills.base import SkillBase, SkillContext, SkillResult, SkillStatus

logger = get_logger(__name__)


class SkillRegistry:
    """Registry for managing and discovering skills."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillBase] = {}

    def register(self, skill: SkillBase) -> None:
        """Register a skill instance."""
        name = skill.metadata.name
        if name in self._skills:
            logger.warning("skill_already_registered", skill=name)
        self._skills[name] = skill
        logger.info(
            "skill_registered",
            skill=name,
            version=skill.metadata.version,
        )

    def get(self, name: str) -> Optional[SkillBase]:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, str]]:
        """List all registered skills with metadata."""
        return [
            {
                "name": s.metadata.name,
                "version": s.metadata.version,
                "description": s.metadata.description,
                "author": s.metadata.author,
                "tags": s.metadata.tags,
            }
            for s in self._skills.values()
        ]

    async def execute(self, name: str, context: SkillContext) -> SkillResult:
        """Execute a skill by name."""
        skill = self.get(name)
        if not skill:
            return SkillResult(
                status=SkillStatus.FAILED,
                errors=[f"Skill not found: {name}"],
            )

        # Validate
        try:
            if not await skill.validate(context):
                return SkillResult(
                    status=SkillStatus.SKIPPED,
                    errors=[f"Skill validation failed: {name}"],
                )
        except Exception as e:
            return SkillResult(
                status=SkillStatus.FAILED,
                errors=[f"Validation error: {str(e)}"],
            )

        # Execute
        import time

        start = time.perf_counter()
        try:
            result = await skill.execute(context)
            result.duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "skill_executed",
                skill=name,
                status=result.status.value,
                duration_ms=result.duration_ms,
            )
            return result
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            logger.exception("skill_execution_failed", skill=name)
            return SkillResult(
                status=SkillStatus.FAILED,
                errors=[str(e)],
                duration_ms=duration,
            )

    async def execute_pipeline(
        self, skill_names: list[str], context: SkillContext
    ) -> dict[str, SkillResult]:
        """Execute multiple skills in sequence, passing results forward."""
        results: dict[str, SkillResult] = {}

        for name in skill_names:
            result = await self.execute(name, context)
            results[name] = result

            # If a skill fails, stop the pipeline
            if result.status == SkillStatus.FAILED:
                logger.warning("pipeline_stopped", failed_skill=name)
                break

            # Pass successful results into context for next skill
            if result.is_success:
                context.metadata[f"skill_result_{name}"] = result.data

        return results


# Global registry
registry = SkillRegistry()
