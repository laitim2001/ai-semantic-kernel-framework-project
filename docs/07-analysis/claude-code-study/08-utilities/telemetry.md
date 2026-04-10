# Telemetry

> Analysis of Claude Code's telemetry system: event schema, collection infrastructure, OpenTelemetry integration, session tracing, and privacy controls.

## Overview

Claude Code's telemetry system uses OpenTelemetry (OTel) as its foundation, providing three signal types: **logs** (events), **metrics** (counters/gauges), and **traces** (spans). The system supports multiple export backends (OTLP, BigQuery, console), respects privacy settings, and integrates with Anthropic's analytics infrastructure.

**Key source files:**
- `src/utils/telemetry/events.ts` — Event logging via OTel
- `src/utils/telemetry/instrumentation.ts` — OTel provider setup (traces, metrics, logs)
- `src/utils/telemetry/sessionTracing.ts` — Session-level trace spans
- `src/utils/telemetry/betaSessionTracing.ts` — Beta session tracing features
- `src/utils/telemetry/perfettoTracing.ts` — Perfetto trace format export
- `src/utils/telemetry/bigqueryExporter.ts` — BigQuery metrics exporter
- `src/utils/telemetry/pluginTelemetry.ts` — Plugin telemetry bridge
- `src/utils/telemetry/skillLoadedEvent.ts` — Skill load tracking
- `src/utils/telemetry/logger.ts` — Custom OTel diagnostic logger
- `src/services/analytics/` — Analytics service (GrowthBook, event logging)

---

## OpenTelemetry Infrastructure

### Provider Setup

`src/utils/telemetry/instrumentation.ts` initializes three OTel providers:

**TracerProvider** — For distributed tracing:
- `BasicTracerProvider` with `BatchSpanProcessor`
- Export via OTLP or console
- Default export interval: `5000ms`

**MeterProvider** — For metrics:
- `MeterProvider` with `PeriodicExportingMetricReader`
- Export via OTLP, BigQuery, Prometheus, or console
- Default export interval: `60000ms`

**LoggerProvider** — For structured event logging:
- `LoggerProvider` with `BatchLogRecordProcessor`
- Export via OTLP or console
- Default export interval: `5000ms`

### Resource Attributes

All telemetry carries standard resource attributes:
- `service.name` — "claude-code"
- `service.version` — Application version
- `host.arch` — System architecture
- Plus OS and host detector attributes from `@opentelemetry/resources`

### Export Backends

| Backend | Signal | Description |
|---------|--------|-------------|
| OTLP | All | Standard OpenTelemetry Protocol export |
| Console | All | Debug output to console |
| BigQuery | Metrics | Custom exporter for Anthropic's BigQuery pipeline |
| Prometheus | Metrics | Prometheus-compatible metrics export |

### Proxy and TLS Support

The instrumentation layer handles:
- HTTP/HTTPS proxy via `HttpsProxyAgent` (from `getProxyUrl()`)
- Proxy bypass rules via `shouldBypassProxy()`
- Custom CA certificates via `getCACertificates()`
- mTLS configuration via `getMTLSConfig()`

---

## Event Logging

### logOTelEvent

`src/utils/telemetry/events.ts` provides the core event logging function:

```typescript
async function logOTelEvent(
  eventName: string,
  metadata: { [key: string]: string | undefined } = {},
): Promise<void>
```

Each event includes:
- `event.name` — Prefixed as `claude_code.<eventName>`
- `event.timestamp` — ISO 8601 timestamp
- `event.sequence` — Monotonically increasing counter for ordering
- `prompt.id` — Current prompt ID (if available)
- `workspace.host_paths` — Desktop app workspace paths (events only, not metrics)
- Standard telemetry attributes from `getTelemetryAttributes()`
- Custom metadata key-value pairs

### Privacy Controls

```typescript
function isUserPromptLoggingEnabled(): boolean {
  return isEnvTruthy(process.env.OTEL_LOG_USER_PROMPTS)
}

function redactIfDisabled(content: string): string {
  return isUserPromptLoggingEnabled() ? content : '<REDACTED>'
}
```

User prompt content is **redacted by default**. Only when `OTEL_LOG_USER_PROMPTS=true` is explicitly set are prompts included in telemetry.

### Event Categories

Events are prefixed with `tengu_` in the analytics system:

| Category | Example Events |
|----------|---------------|
| Agent | `tengu_agent_tool_completed`, `tengu_agent_tool_terminated` |
| Cache | `tengu_cache_eviction_hint` |
| Auto-mode | `tengu_auto_mode_decision` |
| Team | `tengu_team_created`, `tengu_team_deleted` |
| Parse | `tengu_agent_parse_error` |
| File | File operation analytics |

---

## Analytics Service

### GrowthBook Integration

`src/services/analytics/growthbook.ts` provides feature flagging:
- `getFeatureValue_CACHED_MAY_BE_STALE(flag, default)` — Cached flag reads
- `getFeatureValue_CACHED_WITH_REFRESH(flag, default, refreshMs)` — With periodic refresh
- Used throughout for A/B testing and feature gates

### logEvent

`src/services/analytics/index.ts` provides `logEvent()`:

```typescript
function logEvent(
  eventName: string,
  metadata: AnalyticsMetadata,
): void
```

The `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` type is a compile-time safeguard — developers must explicitly cast values, confirming they don't contain code or file paths (privacy protection).

---

## Session Tracing

### Session-Level Spans

`src/utils/telemetry/sessionTracing.ts` manages session-level trace spans:

- **Interaction spans** — Wrap each user interaction (prompt → response)
- `endInteractionSpan()` — Closes the current interaction span
- `isEnhancedTelemetryEnabled()` — Gate for detailed tracing

### Beta Session Tracing

`src/utils/telemetry/betaSessionTracing.ts`:
- `isBetaTracingEnabled()` — Feature gate for beta tracing features
- Extended trace attributes for internal testing
- More detailed span creation for debugging

---

## Perfetto Tracing

`src/utils/telemetry/perfettoTracing.ts` provides Chrome Perfetto trace format:

### Agent Tracking

```typescript
function registerAgent(agentId: string): void
function unregisterAgent(agentId: string): void
function isPerfettoTracingEnabled(): boolean
```

- Agents are registered/unregistered in the Perfetto trace timeline
- Each agent's execution appears as a separate track
- Tool calls within agents appear as nested spans
- Enables visual debugging via Chrome's `chrome://tracing` viewer

### Initialization

`initializePerfettoTracing()` is called during instrumentation setup when the feature is enabled. The trace data is written to a file that can be loaded in Perfetto UI.

---

## BigQuery Exporter

`src/utils/telemetry/bigqueryExporter.ts` provides `BigQueryMetricsExporter`:

- Custom `MetricExporter` implementation for Anthropic's BigQuery pipeline
- Converts OTel metric data points to BigQuery-compatible format
- Handles batching and retry logic
- Used for fleet-wide metrics aggregation and analysis

---

## Plugin Telemetry

`src/utils/telemetry/pluginTelemetry.ts` bridges plugin events to the main telemetry pipeline:

- Plugins emit events through a defined interface
- The bridge validates and forwards events to the OTel pipeline
- Plugin-sourced events are tagged for attribution
- Prevents plugins from injecting arbitrary telemetry data

---

## Skill Load Tracking

`src/utils/telemetry/skillLoadedEvent.ts` tracks skill loading:

- Emits events when skills are loaded (built-in, user, plugin)
- Tracks load time, skill name, source
- Used for understanding skill usage patterns and performance

---

## Diagnostic Logger

`src/utils/telemetry/logger.ts` provides `ClaudeCodeDiagLogger`:

- Custom OTel `DiagLogger` implementation
- Routes OTel internal diagnostics through Claude Code's logging system
- Configurable log level via `DiagLogLevel`
- Prevents OTel internal errors from crashing the application

---

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `OTEL_LOG_USER_PROMPTS` | Enable user prompt logging (privacy) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP export endpoint |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Export protocol (http/protobuf, grpc) |
| `DISABLE_TELEMETRY` | Disable all telemetry |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Disable non-essential network calls |

### Telemetry Attributes

`src/utils/telemetryAttributes.ts` provides `getTelemetryAttributes()`:
- Session ID
- Platform and architecture
- Subscription type
- API provider information
- Build version

### Subscription-Aware Telemetry

Telemetry behavior adapts based on subscription:
- `getSubscriptionType()` — Free, Pro, Teams, Enterprise
- `is1PApiCustomer()` — First-party API customer
- `isClaudeAISubscriber()` — Claude.ai subscriber
- Different export configurations based on customer type

---

## Shutdown and Cleanup

The instrumentation registers cleanup handlers:

```typescript
registerCleanup(async () => {
  await tracerProvider.shutdown()
  await meterProvider.shutdown()
  await loggerProvider.shutdown()
})
```

Providers are properly flushed and shutdown on process exit, with timeout protection (`TelemetryTimeoutError`) to prevent hanging.

---

## Key Design Patterns

1. **Three-signal OTel** — Traces + Metrics + Logs via standard OpenTelemetry APIs
2. **Privacy by default** — User content redacted unless explicitly opted in
3. **Type-safe metadata** — `AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS` prevents accidental PII
4. **Multi-backend export** — OTLP, BigQuery, Prometheus, Console all supported
5. **Feature-gated tracing** — Enhanced/beta tracing behind feature flags
6. **Monotonic sequencing** — Event sequence counter enables correct ordering
7. **Graceful shutdown** — Timeout-protected flush on process exit
8. **Plugin sandboxing** — Plugin telemetry validated and tagged before forwarding
