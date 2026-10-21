# ADR-0005: API Quota Enforcement and Graceful Error Handling for Agnes AI Services

**Date**: 2026-10-21  
**Status**: accepted  
**Deciders**: Engineering Team, User  

## Context

During production usage with real Agnes API credentials, two operational realities emerged:
1. **Agnes Video 2.5 Billing Requirement**: Generating native video via `POST /v1/videos` on an account with zero balance returns:
   `HTTP 403: {"code":"insufficient_user_quota","message":"Insufficient user quota, remaining: ＄0.000000"}`
   Confirming that native video diffusion is strictly a paid service with no $0 promotional tier.
2. **Promotional Free Tier Concurrency & Queuing**: Free promotional image generation (`POST /v1/images/generations` with `agnes-image-2.0-flash`) periodically encounters:
   `HTTP 503: {"error":{"message":"image queue is full, please retry later"}}`
   as well as standard HTTP 429 rate limit thresholds during traffic peaks.

Without structured classification of error responses, quota errors could be mistakenly retried indefinitely, or transient server queue delays could prematurely fail user jobs.

## Decision

We establish an explicit error classification and recovery architecture across the client, pipeline, and UI:

1. **Transient vs. Non-Transient Classification**:
   - **Transient & Retryable**:
     - `HTTP 429 (Too Many Requests)`: Retried with exponential backoff and full jitter (`base_backoff_sec * 2^(attempt-1) * (0.5 + 0.5 * rand)`).
     - `HTTP 5xx (500, 502, 503 Image Queue Full, 504)`: Retried automatically up to `max_retries` (default: 5) to allow temporary server queue congestion to drain.
   - **Non-Transient & Fail-Fast**:
     - `HTTP 403 (insufficient_user_quota / Forbidden)`: Abort immediately without retrying. Parse the quota message and provide actionable resolution instructions.
     - `HTTP 400 (Bad Request)` / `HTTP 401 (Unauthorized)`: Fail-fast with the server's descriptive error message.

2. **Actionable User Guidance for Quota Errors**:
   - When an `insufficient_user_quota` error occurs on `agnes-video-2.5`, surface clear guidance:
     > *"Agnes Video 2.5 requires a paid account balance ($0.025–$0.055/sec). To generate unlimited videos for $0 free, switch to the 'Zero-Cost Pipeline' engine."*

3. **Safe UI State Propagation**:
   - In the Web Studio, propagate API errors directly to the stage status badge and real-time event logs with clear red styling (`#ef4444`), preventing the progress bar from hanging indefinitely.

## Alternatives Considered

### Alternative 1: Automatic Silent Fallback from Native Video to Zero-Cost Engine
- **Pros**: The job completes without showing an error to the user.
- **Cons**: Silently substitutes an AI diffusion video with a 2D Ken Burns slideshow without user consent; surprising and confusing to users who expected fluid diffusion motion.
- **Why not**: Violates predictability. Clear error messaging with 1-click engine switching empowers the user to make the decision.

### Alternative 2: Blind Retries on All HTTP Codes
- **Pros**: Simpler retry loops.
- **Cons**: Retrying 403 quota errors or 400 bad requests wastes system resources, triggers further API penalties, and delays failure reporting.
- **Why not**: Fail-fast on non-transient errors is a core reliability standard.

## Consequences

### Positive
- **High Resilience**: Transient 503 "queue full" and 429 rate-limiting spikes resolve automatically without aborting jobs.
- **Clear User Guidance**: Users immediately understand why a native video generation call failed and know how to proceed (switch to Zero-Cost or top up balance).
- **Zero Wasted Cycles**: Non-retryable quota errors abort instantly.

### Negative
- Requires maintaining explicit status code and error string matching in `client.py`.

### Risks & Mitigations
- **API Error Format Variations**: Fall back to raw response text if the JSON error envelope is missing or non-standard.
