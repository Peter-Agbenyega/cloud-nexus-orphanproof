# Phase P4 Agentic Memory

Phase P4 implements the local OrphanProof intelligence path:

```text
Persistent memory -> Bedrock embeddings -> CockroachDB vector retrieval -> Nova reasoning -> human review
```

## Implemented And Locally Tested

- `BedrockEmbeddingProvider` for Amazon Bedrock Titan Text Embeddings V2 and configurable Cohere Embed v4 fallback
- document embeddings for historical decisions and query embeddings for current-resource retrieval
- deterministic canonical decision memory text
- scoped `decision_embeddings` writer
- CockroachDB cosine vector similarity search with `<=>`
- CockroachDB Cloud Managed MCP read-only client and memory-provider abstraction
- `BedrockReasoningProvider` for Nova Lite Converse
- strict current-verdict validation
- `OrphanProofAgent` orchestration
- `POST /api/v1/resources/{resource_key}/analyze`
- `scripts/p4_index_decisions.py`
- `scripts/p4_verify_mcp.py`
- `scripts/p4_demo_agent.py`

Unit tests use injected fakes and make zero network calls.

## Live Verification Status

- Live CockroachDB vector embedding load with `local.feature-hash-v1`: verified after P4 as part of P5
- Live Titan or Cohere embedding invocation: implemented but currently provider-throttled
- Live Nova Lite reasoning invocation: implemented but currently provider-throttled
- Live CockroachDB Managed MCP read: not yet verified in this P4 coding step

Do not mark Bedrock reasoning as live verified until the safe live gates pass locally.

## Safety Contract

P4 recommendations are advisory only. `REMOVE` is a recommendation for human review, not an action.

P4 always returns:

```text
human_review_required = true
automatic_action_taken = false
decision_persisted = false
```

P4 does not call EC2, RDS, S3, IAM, Lambda, or workload discovery APIs. It only uses Amazon Bedrock Runtime for inference.

## Sponsor Tools

- CockroachDB Distributed Vector Indexing
- CockroachDB Cloud Managed MCP Server
- Amazon Bedrock Titan Text Embeddings V2
- Amazon Bedrock Cohere Embed v4 fallback for 1024-dimensional embeddings
- Amazon Bedrock Nova Lite

## P6 Public Demo Mode

The AWS Lambda demo should use `local.feature-hash-v1` for vector-memory retrieval because live Bedrock calls were throttled during deadline testing. The public vector-memory endpoint does not call Nova, Titan, or Cohere, does not persist a current decision, and does not perform remediation.

The endpoint returns historical nearest-neighbor decisions as evidence only:

```text
analysis_mode = vector_memory
ai_verdict_generated = false
automatic_action_taken = false
human_review_required = true
```
