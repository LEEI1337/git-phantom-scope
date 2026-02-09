"""MLflow Prompt Versioning — Track and version AI prompts.

Integrates with MLflow to version prompt templates, track generation
experiments, and log model performance metrics. This enables A/B testing
of prompts and continuous improvement of generation quality.

Usage:
    tracker = PromptTracker(mlflow_uri="http://localhost:5000")
    run_id = tracker.start_generation_run(profile_data, template_id)
    tracker.log_prompt(run_id, prompt_dict)
    tracker.log_result(run_id, quality_score, latency, model_used)
    tracker.end_run(run_id)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class PromptTracker:
    """Track prompt versions, generation experiments, and quality metrics.

    Uses MLflow to log experiment runs. Falls back gracefully if MLflow
    is not available (logs warning, continues without tracking).
    """

    def __init__(self, mlflow_uri: str | None = None) -> None:
        self._mlflow_uri = mlflow_uri
        self._mlflow = None
        self._experiment_id: str | None = None
        self._active_runs: dict[str, Any] = {}
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazy-initialize MLflow connection.

        Returns:
            True if MLflow is available, False otherwise.
        """
        if self._initialized:
            return self._mlflow is not None

        self._initialized = True
        try:
            import mlflow

            uri = self._mlflow_uri or get_settings().mlflow_tracking_uri
            mlflow.set_tracking_uri(uri)
            mlflow.set_experiment("gps-prompt-versioning")
            self._mlflow = mlflow
            self._experiment_id = mlflow.get_experiment_by_name(
                "gps-prompt-versioning"
            ).experiment_id
            logger.info("mlflow_initialized", tracking_uri=uri)
            return True
        except Exception as e:
            logger.warning("mlflow_unavailable", error=str(e))
            self._mlflow = None
            return False

    def start_generation_run(
        self,
        template_id: str,
        model_provider: str,
        archetype: str,
        tier: str = "free",
        tags: dict[str, str] | None = None,
    ) -> str:
        """Start a new MLflow run for a generation experiment.

        Args:
            template_id: Image/README template used.
            model_provider: AI model provider (gemini, openai, etc.)
            archetype: Developer archetype classification.
            tier: User tier (free, pro, enterprise).
            tags: Additional tags for the run.

        Returns:
            Run ID string (or a local fallback ID if MLflow unavailable).
        """
        run_tags = {
            "template_id": template_id,
            "model_provider": model_provider,
            "archetype": archetype,
            "tier": tier,
            **(tags or {}),
        }

        if self._ensure_initialized() and self._mlflow:
            try:
                run = self._mlflow.start_run(
                    experiment_id=self._experiment_id,
                    tags=run_tags,
                )
                run_id = run.info.run_id
                self._active_runs[run_id] = {
                    "start_time": time.time(),
                    "mlflow": True,
                }
                logger.info("mlflow_run_started", run_id=run_id)
                return run_id
            except Exception as e:
                logger.warning("mlflow_start_run_failed", error=str(e))

        # Fallback: local tracking without MLflow
        fallback_id = hashlib.sha256(
            f"{template_id}:{model_provider}:{time.time()}".encode()
        ).hexdigest()[:16]
        self._active_runs[fallback_id] = {
            "start_time": time.time(),
            "mlflow": False,
            "tags": run_tags,
        }
        return fallback_id

    def log_prompt(
        self,
        run_id: str,
        prompt: dict[str, str] | str,
        prompt_version: str | None = None,
    ) -> None:
        """Log the prompt used in a generation run.

        Args:
            run_id: Active run ID.
            prompt: The prompt dict or string sent to the model.
            prompt_version: Optional semantic version of the prompt template.
        """
        run_info = self._active_runs.get(run_id)
        if not run_info:
            return

        # Compute prompt hash for deduplication / version tracking
        prompt_str = json.dumps(prompt, sort_keys=True) if isinstance(prompt, dict) else prompt
        prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:12]

        if run_info.get("mlflow") and self._mlflow:
            try:
                self._mlflow.log_param("prompt_hash", prompt_hash)
                if prompt_version:
                    self._mlflow.log_param("prompt_version", prompt_version)
                # Log prompt as artifact (text file)
                import os
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, prefix="prompt_"
                ) as f:
                    f.write(prompt_str)
                    temp_path = f.name

                try:
                    self._mlflow.log_artifact(temp_path, "prompts")
                finally:
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning("mlflow_log_prompt_failed", error=str(e))
        else:
            run_info["prompt_hash"] = prompt_hash

    def log_result(
        self,
        run_id: str,
        success: bool,
        latency_seconds: float,
        model_used: str,
        output_size_bytes: int = 0,
        quality_score: float | None = None,
    ) -> None:
        """Log the result of a generation run.

        Args:
            run_id: Active run ID.
            success: Whether generation succeeded.
            latency_seconds: Total generation time.
            model_used: Specific model identifier (e.g., "gemini-2.0-flash").
            output_size_bytes: Size of generated output.
            quality_score: Optional quality score (0-1) from evaluation.
        """
        run_info = self._active_runs.get(run_id)
        if not run_info:
            return

        metrics = {
            "success": 1.0 if success else 0.0,
            "latency_seconds": latency_seconds,
            "output_size_bytes": float(output_size_bytes),
        }
        if quality_score is not None:
            metrics["quality_score"] = quality_score

        if run_info.get("mlflow") and self._mlflow:
            try:
                self._mlflow.log_param("model_used", model_used)
                self._mlflow.log_metrics(metrics)
            except Exception as e:
                logger.warning("mlflow_log_result_failed", error=str(e))
        else:
            run_info["metrics"] = metrics
            run_info["model_used"] = model_used

    def end_run(self, run_id: str, status: str = "FINISHED") -> None:
        """End an MLflow run.

        Args:
            run_id: Active run ID.
            status: Run status (FINISHED, FAILED, KILLED).
        """
        run_info = self._active_runs.pop(run_id, None)
        if not run_info:
            return

        total_time = time.time() - run_info["start_time"]

        if run_info.get("mlflow") and self._mlflow:
            try:
                self._mlflow.log_metric("total_time_seconds", total_time)
                self._mlflow.end_run(status=status)
            except Exception as e:
                logger.warning("mlflow_end_run_failed", error=str(e))

        logger.info(
            "generation_run_completed",
            run_id=run_id,
            status=status,
            total_time=round(total_time, 2),
        )

    def get_best_prompt_version(
        self,
        template_id: str,
        model_provider: str,
        metric: str = "quality_score",
    ) -> str | None:
        """Query MLflow for the best-performing prompt version.

        Args:
            template_id: Template to query.
            model_provider: Provider to query.
            metric: Metric to optimize (default: quality_score).

        Returns:
            Best prompt version string, or None if not available.
        """
        if not self._ensure_initialized() or not self._mlflow:
            return None

        try:
            from mlflow.tracking import MlflowClient

            client = MlflowClient()
            runs = client.search_runs(
                experiment_ids=[self._experiment_id],
                filter_string=(
                    f"tags.template_id = '{template_id}' "
                    f"AND tags.model_provider = '{model_provider}'"
                ),
                order_by=[f"metrics.{metric} DESC"],
                max_results=1,
            )
            if runs:
                return runs[0].data.params.get("prompt_version")
            return None
        except Exception as e:
            logger.warning("mlflow_query_failed", error=str(e))
            return None


# Module-level singleton
_tracker: PromptTracker | None = None


def get_prompt_tracker() -> PromptTracker:
    """Get or create the global PromptTracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = PromptTracker()
    return _tracker
