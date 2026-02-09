---
name: "deploy-service"
description: "Deploy and configure Git Phantom Scope services using Docker Compose, including health checks, monitoring, and production hardening."
mode: "agent"
---

# Deploy Service

## Context
Deploy Git Phantom Scope services using Docker Compose for development and Docker/Kubernetes for production.

## Docker Compose Service Definitions

### Service Naming Convention
All services use `gps-` prefix:
```yaml
services:
  gps-backend:     # FastAPI application
  gps-frontend:    # Next.js application
  gps-postgres:    # PostgreSQL (analytics only)
  gps-redis:       # Redis (cache/sessions)
  gps-celery:      # Celery worker (async jobs)
  gps-mlflow:      # MLflow tracking server
  gps-prometheus:  # Prometheus metrics
  gps-grafana:     # Grafana dashboards
```

### Health Check Pattern
```yaml
gps-backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

### Environment Variables
```yaml
# REQUIRED environment variables
GPS_DATABASE_URL: postgresql+asyncpg://gps:${POSTGRES_PASSWORD}@gps-postgres:5432/gps_analytics
GPS_REDIS_URL: redis://gps-redis:6379/0
GPS_GITHUB_TOKEN: ${GITHUB_TOKEN}  # Optional: for higher rate limits
GPS_SECRET_KEY: ${SECRET_KEY}
GPS_ENVIRONMENT: development|staging|production
GPS_LOG_LEVEL: INFO
GPS_RATE_LIMIT_ENABLED: true
GPS_CORS_ORIGINS: http://localhost:3000
```

### Resource Limits
```yaml
gps-backend:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

## Deployment Checklist
- [ ] All `.env` variables configured
- [ ] PostgreSQL initialized with schema
- [ ] Redis accessible and responsive
- [ ] Health checks passing for all services
- [ ] Prometheus scraping metrics endpoints
- [ ] Grafana dashboards imported
- [ ] Rate limiting operational
- [ ] HTTPS configured (production)
- [ ] Backup procedures documented
- [ ] Monitoring alerts configured

## Production Hardening
- [ ] Disable debug mode
- [ ] Enable HTTPS everywhere
- [ ] Configure proper CORS origins
- [ ] Set resource limits on all containers
- [ ] Enable Docker secrets for credentials
- [ ] Configure log rotation
- [ ] Set up health check alerts
- [ ] Enable rate limiting
- [ ] Configure reverse proxy (Traefik/Nginx)

## Implementation Files
- `docker-compose.yml` - Development stack
- `docker-compose.prod.yml` - Production overrides
- `infra/docker/` - Dockerfiles
- `infra/k8s/` - Kubernetes manifests
- `infra/monitoring/` - Prometheus/Grafana configs
