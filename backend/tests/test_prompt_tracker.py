"""Tests for MLflow prompt versioning tracker."""

from unittest.mock import MagicMock

import pytest

from services.prompt_tracker import PromptTracker, get_prompt_tracker


@pytest.fixture
def tracker():
    """Create a PromptTracker with MLflow disabled."""
    t = PromptTracker(mlflow_uri="http://fake:5000")
    # Force _initialized so it won't try to import mlflow
    t._initialized = True
    t._mlflow = None
    return t


@pytest.fixture
def mock_mlflow():
    """Create a mock mlflow module."""
    mock = MagicMock()
    mock.get_experiment_by_name.return_value = MagicMock(experiment_id="exp-1")
    return mock


@pytest.fixture
def tracker_with_mlflow(mock_mlflow):
    """Create a PromptTracker with mocked MLflow."""
    t = PromptTracker(mlflow_uri="http://fake:5000")
    t._initialized = True
    t._mlflow = mock_mlflow
    t._experiment_id = "exp-1"
    return t


class TestPromptTrackerInit:
    def test_default_not_initialized(self):
        t = PromptTracker()
        assert t._initialized is False
        assert t._mlflow is None

    def test_custom_uri(self):
        t = PromptTracker(mlflow_uri="http://custom:9000")
        assert t._mlflow_uri == "http://custom:9000"

    def test_lazy_initialization(self, tracker):
        # Already forced initialized
        assert tracker._initialized is True


class TestFallbackMode:
    """Tests for operation when MLflow is unavailable."""

    def test_start_run_returns_fallback_id(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="portfolio_banner",
            model_provider="gemini",
            archetype="ai_indie_hacker",
        )
        assert isinstance(run_id, str)
        assert len(run_id) == 16  # SHA-256 hex[:16]

    def test_fallback_run_tracked_locally(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="neon_circuit",
            model_provider="openai",
            archetype="full_stack_polyglot",
            tier="pro",
        )
        assert run_id in tracker._active_runs
        run_info = tracker._active_runs[run_id]
        assert run_info["mlflow"] is False
        assert "start_time" in run_info
        assert run_info["tags"]["tier"] == "pro"

    def test_log_prompt_stores_hash_locally(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="test", model_provider="gemini", archetype="test"
        )
        tracker.log_prompt(run_id, {"system": "test", "user": "hello"})
        assert "prompt_hash" in tracker._active_runs[run_id]

    def test_log_prompt_string_input(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="test", model_provider="gemini", archetype="test"
        )
        tracker.log_prompt(run_id, "simple prompt text")
        assert "prompt_hash" in tracker._active_runs[run_id]

    def test_log_prompt_unknown_run_id_is_noop(self, tracker):
        # Should not raise
        tracker.log_prompt("nonexistent-run", {"prompt": "test"})

    def test_log_result_stores_metrics_locally(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="test", model_provider="gemini", archetype="test"
        )
        tracker.log_result(
            run_id=run_id,
            success=True,
            latency_seconds=1.5,
            model_used="gemini-2.0-flash",
            output_size_bytes=50000,
            quality_score=0.85,
        )
        metrics = tracker._active_runs[run_id]["metrics"]
        assert metrics["success"] == 1.0
        assert metrics["latency_seconds"] == 1.5
        assert metrics["quality_score"] == 0.85

    def test_log_result_without_quality_score(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="test", model_provider="gemini", archetype="test"
        )
        tracker.log_result(
            run_id=run_id,
            success=False,
            latency_seconds=0.5,
            model_used="gemini-2.0-flash",
        )
        metrics = tracker._active_runs[run_id]["metrics"]
        assert metrics["success"] == 0.0
        assert "quality_score" not in metrics

    def test_end_run_removes_from_active(self, tracker):
        run_id = tracker.start_generation_run(
            template_id="test", model_provider="gemini", archetype="test"
        )
        assert run_id in tracker._active_runs
        tracker.end_run(run_id, status="FINISHED")
        assert run_id not in tracker._active_runs

    def test_end_run_unknown_id_is_noop(self, tracker):
        # Should not raise
        tracker.end_run("unknown-id")

    def test_get_best_prompt_returns_none_fallback(self, tracker):
        result = tracker.get_best_prompt_version("template", "gemini")
        assert result is None


class TestMLflowMode:
    """Tests for operation when MLflow is available (mocked)."""

    def test_start_run_uses_mlflow(self, tracker_with_mlflow, mock_mlflow):
        mock_run = MagicMock()
        mock_run.info.run_id = "mlflow-run-123"
        mock_mlflow.start_run.return_value = mock_run

        run_id = tracker_with_mlflow.start_generation_run(
            template_id="portfolio_banner",
            model_provider="gemini",
            archetype="ai_indie_hacker",
        )

        assert run_id == "mlflow-run-123"
        mock_mlflow.start_run.assert_called_once()

    def test_start_run_mlflow_failure_falls_back(self, tracker_with_mlflow, mock_mlflow):
        mock_mlflow.start_run.side_effect = Exception("MLflow down")

        run_id = tracker_with_mlflow.start_generation_run(
            template_id="test",
            model_provider="gemini",
            archetype="test",
        )
        # Should still return a fallback ID
        assert isinstance(run_id, str)
        assert len(run_id) == 16

    def test_log_result_calls_mlflow(self, tracker_with_mlflow, mock_mlflow):
        mock_run = MagicMock()
        mock_run.info.run_id = "mlflow-run-456"
        mock_mlflow.start_run.return_value = mock_run

        run_id = tracker_with_mlflow.start_generation_run(
            template_id="test",
            model_provider="gemini",
            archetype="test",
        )
        tracker_with_mlflow.log_result(
            run_id=run_id,
            success=True,
            latency_seconds=2.0,
            model_used="gemini-2.0-flash",
        )

        mock_mlflow.log_param.assert_called_with("model_used", "gemini-2.0-flash")
        mock_mlflow.log_metrics.assert_called_once()

    def test_end_run_calls_mlflow(self, tracker_with_mlflow, mock_mlflow):
        mock_run = MagicMock()
        mock_run.info.run_id = "mlflow-run-789"
        mock_mlflow.start_run.return_value = mock_run

        run_id = tracker_with_mlflow.start_generation_run(
            template_id="test",
            model_provider="gemini",
            archetype="test",
        )
        tracker_with_mlflow.end_run(run_id, status="FINISHED")

        mock_mlflow.log_metric.assert_called_once()
        mock_mlflow.end_run.assert_called_once_with(status="FINISHED")


class TestCustomTags:
    def test_tags_passed_to_mlflow(self, tracker_with_mlflow, mock_mlflow):
        mock_run = MagicMock()
        mock_run.info.run_id = "run-tags"
        mock_mlflow.start_run.return_value = mock_run

        tracker_with_mlflow.start_generation_run(
            template_id="neon_circuit",
            model_provider="openai",
            archetype="backend_architect",
            tier="pro",
            tags={"custom_tag": "value"},
        )

        call_kwargs = mock_mlflow.start_run.call_args
        tags = call_kwargs[1]["tags"] if "tags" in call_kwargs[1] else call_kwargs.kwargs["tags"]
        assert tags["custom_tag"] == "value"
        assert tags["tier"] == "pro"


class TestGetPromptTrackerSingleton:
    def test_returns_instance(self):
        # Reset singleton
        import services.prompt_tracker as mod

        mod._tracker = None
        tracker = get_prompt_tracker()
        assert isinstance(tracker, PromptTracker)

    def test_returns_same_instance(self):
        import services.prompt_tracker as mod

        mod._tracker = None
        t1 = get_prompt_tracker()
        t2 = get_prompt_tracker()
        assert t1 is t2
