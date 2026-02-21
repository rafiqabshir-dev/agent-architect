# 07 — Production Checklist

## Everything You Need Before Going Live — Any Agent

---

## Pre-Deployment Checklist

### Reliability
- [ ] Shadow mode run for 5+ days with acceptable metrics
- [ ] All edge cases from shadow mode handled in code
- [ ] Graceful handling of LLM API downtime (retry with exponential backoff, skip cycle if persistent)
- [ ] Graceful handling of data source downtime (retry, don't duplicate processing)
- [ ] Malformed LLM responses handled (JSON parse failures, missing fields, unexpected values)
- [ ] Token limit handling (truncate long inputs, not fail)
- [ ] Idempotent processing (running the same input twice doesn't create duplicates)
- [ ] Rollback plan documented (how to revert to previous version in <5 minutes)

### Security
- [ ] All API credentials stored in environment variables (not in code)
- [ ] OAuth token refresh working (test by expiring token manually)
- [ ] No sensitive data logged (PII, credentials, full email bodies)
- [ ] Rate limiting on any externally-triggered endpoints
- [ ] Database credentials rotatable without redeployment

### Monitoring & Alerting
- [ ] Heartbeat monitoring active (uptime service like Betteruptime, Healthchecks.io)
- [ ] Output delivery alert (notify if expected output doesn't happen by deadline)
- [ ] LLM API health monitoring (alert on consecutive failures)
- [ ] Data source auth monitoring (alert when token refresh fails)
- [ ] Cost alerts (notify if daily spend exceeds 2x baseline)
- [ ] Error rate alert (notify if >5% of runs fail in an hour)

### Observability
- [ ] LLM tracing active (LangSmith or equivalent) — every LLM call logged with full input/output
- [ ] Structured logging (JSON format) with correlation IDs per run
- [ ] Key metrics tracked: inputs processed, classification distribution, latency, token usage, error count
- [ ] Ability to replay any specific run from traces within 30 seconds

### Evaluation
- [ ] Eval pipeline automated and runnable in CI
- [ ] Metrics baseline established on holdout set
- [ ] Weekly scorecard template ready
- [ ] Feedback collection mechanism in place (reactions, correction commands, etc.)

---

## Infrastructure Recommendations

| Component | Simple (Start Here) | Robust (Scale To) |
|-----------|-------------------|-------------------|
| **Runtime** | Docker on Railway / Fly.io / VPS | Kubernetes |
| **Database** | Managed PostgreSQL (Supabase, Neon) | Self-managed PG with replicas |
| **Scheduler** | node-cron / schedule (in-process) | BullMQ / Temporal / cloud scheduler |
| **Secrets** | Platform env vars | HashiCorp Vault / AWS Secrets Manager |
| **Logs** | Console + log file | Structured → Datadog / Grafana Loki |
| **Metrics** | Manual weekly scorecard | Prometheus + Grafana |
| **Tracing** | LangSmith free tier | LangSmith paid / self-hosted tracing |
| **Alerting** | Healthchecks.io free tier | PagerDuty / Opsgenie |

**Start simple. Upgrade when the simple version becomes a bottleneck, not before.**

---

## Monitoring What Matters

### The Four Questions

Your monitoring should answer these at a glance:

1. **Is it running?** → Heartbeat check
2. **Is it working correctly?** → Output delivery + accuracy metrics
3. **Is it costing what I expect?** → Daily token/API spend
4. **Is it getting better or worse?** → Weekly scorecard trend

### Operational Metrics to Track

| Metric | What to Alert On |
|--------|-----------------|
| Inputs processed per cycle | Drop to 0 (agent not running or data source broken) |
| Classification distribution | Sudden shift (>20% change in any category week-over-week) |
| LLM latency per call | p95 > 30 seconds |
| Error count per day | >5% of runs |
| Token usage per day | >2x baseline |
| Output delivery | Not delivered by expected time |

---

## Failure Modes & Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| **LLM API down** | Consecutive 5xx errors | Retry with backoff → skip cycle → alert after 3 skips |
| **Data source API down** | Auth or connection errors | Retry with backoff → skip cycle → alert |
| **OAuth token expired** | 401 response | Auto-refresh → if refresh fails, alert immediately |
| **Database unreachable** | Connection timeout | Retry → buffer in memory → alert |
| **Agent stuck in loop** | Cycle duration > 10x normal | Kill and restart → alert |
| **Cost spike** | Daily spend > 2x baseline | Alert → investigate (unexpected input volume? prompt regression?) |
| **Accuracy regression** | Weekly scorecard shows decline | Investigate recent changes → rollback prompt/code if needed |
| **Process crash** | Heartbeat stops | Auto-restart (Docker restart policy) → alert if repeated |

---

## Cost Management

### Estimation Template

| Operation | Calls/Day | ~Tokens/Call (in + out) | Price/1K Tokens | Daily Cost |
|-----------|-----------|------------------------|----------------|------------|
| [LLM Node 1] | — | — | — | — |
| [LLM Node 2] | — | — | — | — |
| [API calls] | — | — | — | — |
| [Database] | — | — | — | — |
| [Hosting] | — | — | — | — |
| **Total** | | | | **—** |

### Cost Optimization Levers

| Lever | Impact | Trade-off |
|-------|--------|-----------|
| Use a cheaper model for simple tasks | High | Possible accuracy drop — measure it |
| Reduce input size (truncate, extract key parts) | Medium | Might lose important context |
| Cache repeated inputs | Medium | Stale data risk, complexity |
| Batch processing instead of real-time | Medium | Higher latency |
| Use deterministic code instead of LLM for routing | High | None (strictly better if the routing logic is known) |

---

## Day-1 vs Day-30 Operations

### Day 1 (Just Shipped)
- Check output manually every morning
- Review traces for any obvious failures
- Track metrics in a spreadsheet
- Respond to alerts personally

### Day 30 (Stabilized)
- Automated eval runs weekly in CI
- Metrics dashboard with alerting
- Feedback loop collecting corrections
- Monthly prompt refinement cycle
- Output trusted without daily manual review

### Day 90 (Mature)
- Eval dataset > 200 cases
- Prompt changelog with measured improvements
- Consider Phase 7 expansions
- Cost optimized based on real data
- Agent runs reliably with minimal oversight
