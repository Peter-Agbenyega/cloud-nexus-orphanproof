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

- Live CockroachDB vector embedding load: not yet verified in this P4 coding step
- Live Titan or Cohere embedding invocation: not yet verified in this P4 coding step
- Live Nova Lite reasoning invocation: not yet verified in this P4 coding step
- Live CockroachDB Managed MCP read: not yet verified in this P4 coding step

Do not mark these as live verified until the safe live gates pass locally.

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
