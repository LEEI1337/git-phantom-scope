"""Prometheus metrics for monitoring.

Tracks request latency, model call durations, generation success rates,
and queue depths for comprehensive observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# Application info
APP_INFO = Info("gps_app", "Git Phantom Scope application info")

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "gps_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "gps_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# GitHub API metrics
GITHUB_API_CALLS = Counter(
    "gps_github_api_calls_total",
    "Total GitHub API calls",
    ["endpoint", "status"],
)

GITHUB_API_DURATION = Histogram(
    "gps_github_api_duration_seconds",
    "GitHub API call duration",
    ["endpoint"],
)

GITHUB_CACHE_HITS = Counter(
    "gps_github_cache_hits_total",
    "GitHub data cache hits",
)

GITHUB_CACHE_MISSES = Counter(
    "gps_github_cache_misses_total",
    "GitHub data cache misses",
)

# Model connector metrics
MODEL_CALLS = Counter(
    "gps_model_calls_total",
    "Total AI model API calls",
    ["provider", "model", "type", "status"],
)

MODEL_CALL_DURATION = Histogram(
    "gps_model_call_duration_seconds",
    "AI model API call duration",
    ["provider", "model"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Generation metrics
GENERATIONS_TOTAL = Counter(
    "gps_generations_total",
    "Total profile generations",
    ["template", "tier", "status"],
)

GENERATION_DURATION = Histogram(
    "gps_generation_duration_seconds",
    "Profile generation duration",
    ["template"],
    buckets=(5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "gps_queue_depth",
    "Current generation queue depth",
)

ACTIVE_SESSIONS = Gauge(
    "gps_active_sessions",
    "Currently active sessions",
)

# Rate limiting
RATE_LIMIT_HITS = Counter(
    "gps_rate_limit_hits_total",
    "Total rate limit hits",
    ["endpoint", "limit_type"],
)

# Scoring metrics
SCORING_DURATION = Histogram(
    "gps_scoring_duration_seconds",
    "Profile scoring duration",
)

ARCHETYPES_ASSIGNED = Counter(
    "gps_archetypes_assigned_total",
    "Developer archetypes assigned",
    ["archetype"],
)
