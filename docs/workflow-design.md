# Workflow Design

`HarnessWorkflow` is a bounded control transaction. It validates and reviews LLM
output before a host application decides whether to perform a real side effect.
The workflow never performs that side effect itself.

## Decision Semantics

| Decision | Meaning |
|---|---|
| `approved` | Output passed review. The host may continue with its own checks. |
| `rejected` | Valid output repeatedly failed business review within policy limits. |
| `error` | A system, adapter, configuration, or unexpected execution failure occurred. |

A system failure must never become `rejected`. Hosts commonly handle a business
rejection and a service outage differently.

## Routing Policy

```mermaid
flowchart TD
    A["Infer"] --> B{"Output produced?"}
    B -- "Yes" --> C["Review"]
    B -- "No: retryable system error" --> D{"Inference attempts remain?"}
    B -- "No: non-retryable system error" --> E["Return error"]
    D -- "Yes" --> A
    D -- "No" --> E
    C --> F{"Review action"}
    F -- "approve" --> G["Return approved"]
    F -- "reject" --> J["Return rejected"]
    F -- "review_again" --> H{"Review attempts remain?"}
    H -- "Yes" --> C
    H -- "No" --> J
    F -- "legacy reviewer rejection" --> I{"Inference attempts remain?"}
    I -- "Yes" --> A
    I -- "No" --> J
```

`intelligent_harness.errors.classify_inference_error()` keeps SDK-specific
exceptions outside the graph. Standard connection and timeout failures, plus
known SDK exception names, are retryable. Other inference failures are
non-retryable unless an adapter explicitly raises `RetryableInferenceError`.

## Semantic Layered Review

The `marketing_copy` scenario uses `SemanticLayeredReviewer`. It embeds the
candidate output, compares it with configured risk samples, and routes the
highest cosine similarity score through three configurable bands. Sample
vectors are cached when the reviewer is created.

The default policy is:

| Similarity | Action |
|---|---|
| `< 0.6` | `approve` |
| `0.6` to `0.8`, inclusive | `review_again`: ask the LLM reviewer to re-evaluate |
| `> 0.8` | `reject` |

`review_again` is bounded by `policy.max_review_attempts`. The result metadata
records the matched risk intent, sample text, cosine similarity, normalized
Euclidean distance, thresholds, and selected semantic action.

## Events

Each failed inference emits `inference_failed`, and a reviewer exception emits
`review_failed`. A business rejection emits `final_rejected`; a handled system
failure emits `final_error`. Both final event types are severity `1`.
