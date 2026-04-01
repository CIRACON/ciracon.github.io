---
title: "LLM Fundamentals for AI Engineering"
category: "AI Engineering"
description: "A technical overview of large language models, covering core concepts, architecture, training, and practical engineering considerations."
date: "2026-03-31"
slug: "llm-fundamentals-for-ai-engineering"
---

<p>Most teams treat LLMs like a smarter API call. That works for demos and fails in production. Once you put a model behind a real product, the hard parts show up fast: latency budgets, prompt drift, bad retrieval, missing evals, runaway cost, and no clean way to debug failures.</p>

<p>If you're building an AI platform, we recommend treating LLMs as a distributed system component, not a feature flag. That means explicit contracts, observability, fallback paths, and versioned inputs. The model matters, but the surrounding system matters more.</p>

<div class="diagram">
  <div class="diagram-title">Production LLM Request Path</div>
  <div class="diagram-flow">
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">1</span>
        <span class="node-label">Preprocess</span>
        <span class="node-sub">Validate and shape input</span>
        <span class="node-tooltip">Normalize user input, enforce policy checks, and build a versioned prompt payload before calling any model.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">2</span>
        <span class="node-label">Infer</span>
        <span class="node-sub">Route to model</span>
        <span class="node-tooltip">Choose the model, apply retries and timeouts, and capture request metadata for cost and latency tracking.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-node">
      <span class="node-num">3</span>
      <span class="node-label">Postprocess</span>
      <span class="node-sub">Validate and log output</span>
      <span class="node-tooltip">Check structured output, apply guardrails, store traces, and trigger fallback logic if the response is invalid.</span>
    </div>
  </div>
  <div class="diagram-hint">Hover over each step for details</div>
</div>

<h2>Build an LLM layer, not scattered model calls</h2>

<p>The first architecture mistake we keep seeing is model access spread across services. One team calls OpenAI directly, another uses Anthropic, a third wraps a local vLLM endpoint, and nobody can answer basic questions like which prompts are live, what the p95 latency is, or why cost doubled last week.</p>

<p>Put a thin LLM gateway in front of every provider. This does not need to be complicated. A FastAPI or Go service is enough if it gives you a few things:</p>

<ul>
  <li>Provider abstraction: OpenAI, Anthropic, Gemini, Azure OpenAI, or a local endpoint like vLLM or TGI.</li>
  <li>Prompt versioning: store templates in Git, include a prompt version in every request.</li>
  <li>Routing rules: cheap model for classification, stronger model for synthesis, fallback model on timeout.</li>
  <li>Observability: request ID, user ID, model, tokens, latency, retry count, and cache hit status.</li>
  <li>Policy hooks: PII redaction, content filtering, and output schema validation.</li>
</ul>

<p>We'd rather have one boring internal API like <code>POST /v1/generate</code> than let every application team invent its own prompt stack. It gives you one place to enforce timeouts, one place to meter usage, and one place to roll out model changes safely.</p>

<h2>Pick model strategy by workload, not by leaderboard</h2>

<p>Most teams overpay for large models because they don't split workloads. That's lazy architecture. Use different models for different jobs.</p>

<p>For example:</p>

<ul>
  <li><strong>Classification, tagging, routing:</strong> small model, low temperature, strict schema output.</li>
  <li><strong>Summarization and extraction:</strong> mid-tier model with JSON mode or tool calling.</li>
  <li><strong>Complex synthesis or agentic planning:</strong> stronger model, but behind tighter quotas.</li>
  <li><strong>High-volume internal workloads:</strong> self-hosted model on vLLM if throughput matters more than absolute quality.</li>
</ul>

<p>If you're running on Kubernetes, self-hosting only makes sense when you have sustained volume and a team that can operate GPU workloads. Otherwise, use a managed API and spend your time on evals and product quality. We would not self-host a flagship model just to save a little per-token cost while the rest of the stack is still unstable.</p>

<p>When you do self-host, vLLM is the default starting point. It gives you solid throughput, paged attention, and OpenAI-compatible serving. Pair it with KServe or a plain Deployment plus HPA if you already know your traffic shape. For GPU scheduling, use the NVIDIA device plugin and keep node pools isolated. Mixing general workloads and GPU inference on the same nodes usually creates noisy-neighbor problems and ugly autoscaling behavior.</p>

<h2>Prompt engineering is configuration management</h2>

<p>Prompts are not product copy. They are executable configuration. Treat them the same way you treat Terraform modules or Kubernetes manifests.</p>

<p>That means:</p>

<ul>
  <li>Store prompts in Git.</li>
  <li>Use templates with explicit variables.</li>
  <li>Version every prompt and system instruction.</li>
  <li>Test prompt changes against a fixed evaluation set before rollout.</li>
  <li>Log the exact rendered prompt for each request, with secrets redacted.</li>
</ul>

<p>A common anti-pattern is editing prompts in a web console with no review path. It feels fast until output quality regresses and nobody can reproduce the previous behavior. We strongly prefer prompt files in the repo plus a small registry table that maps application features to prompt versions.</p>

<p>Structured output is also worth the effort. If the downstream system expects fields, ask for JSON and validate it with Pydantic, JSON Schema, or Zod. Do not parse free-form prose with regex and call that production-ready. That path ends with brittle code and support tickets.</p>

<h2>Retrieval helps, but only if you evaluate it properly</h2>

<p>RAG is where teams burn a lot of time. The usual mistake is optimizing embeddings and vector databases before they have a retrieval evaluation loop. That is backwards.</p>

<p>Start with a simple stack: chunk documents, embed them with a decent embedding model, store them in PostgreSQL with pgvector or in OpenSearch, and rerank top-k results if needed. For many internal knowledge use cases, pgvector is enough. We would not introduce a dedicated vector database on day one unless scale or feature requirements are already clear.</p>

<p>The important part is evaluation:</p>

<ul>
  <li>Can the system retrieve the right chunk for known questions?</li>
  <li>Does chunking preserve enough context to answer correctly?</li>
  <li>Are stale documents still being served?</li>
  <li>Does metadata filtering actually narrow the result set?</li>
</ul>

<p>If you skip this, the model gets blamed for retrieval failures it cannot fix. A strong model with bad context still gives bad answers, just more confidently.</p>

<h2>Observability should cover prompts, tokens, and failures</h2>

<p>Standard API metrics are not enough. You need traces that explain why the model did what it did and how much it cost.</p>

<p>At minimum, capture:</p>

<ul>
  <li>Prompt version and rendered prompt hash.</li>
  <li>Model name, provider, and inference parameters.</li>
  <li>Input and output token counts.</li>
  <li>Latency by phase: retrieval, model call, postprocessing.</li>
  <li>Validation failures, fallback usage, and retry reasons.</li>
  <li>User or tenant attribution for chargeback and abuse detection.</li>
</ul>

<p>OpenTelemetry works well here. Emit spans around retrieval, model inference, and validation. Send metrics to Prometheus, traces to Tempo or Jaeger, and logs to Loki or Elasticsearch. If you're already using Langfuse, Helicone, or OpenLIT, that's fine too, but don't outsource your entire observability story to a single AI-specific tool. Keep the core telemetry in the same stack your platform team already operates.</p>

<h2>What usually goes wrong</h2>

<p>The most common failure modes are predictable.</p>

<ul>
  <li><strong>No evaluation set:</strong> teams ship prompt and model changes based on vibes. Quality drifts and nobody notices until users complain.</li>
  <li><strong>No output validation:</strong> one malformed JSON response breaks a downstream workflow and turns into a flaky incident.</li>
  <li><strong>Retry storms:</strong> naive client retries multiply provider errors and spike both latency and cost.</li>
  <li><strong>Unbounded context:</strong> developers keep appending conversation history until token cost explodes and latency becomes unacceptable.</li>
  <li><strong>Weak tenancy controls:</strong> one abusive customer or internal batch job consumes the entire budget.</li>
  <li><strong>Shadow prompts:</strong> application teams fork prompt logic locally, so central improvements never propagate.</li>
</ul>

<p>The fix is not more prompt tweaking. The fix is better platform discipline: budgets, schemas, evals, and routing controls.</p>

<h2>Lessons learned from running LLM workloads</h2>

<p>First, latency matters more than model quality for a surprising number of use cases. If the response takes 12 seconds, users stop caring that it was slightly smarter. We would rather ship a faster model with tighter prompts and retrieval than a slower premium model everywhere.</p>

<p>Second, caching works, but only for narrow patterns. Semantic caching sounds great, but exact-match or normalized-input caching is easier to reason about and much safer. Use Redis for deterministic cache keys before you get fancy.</p>

<p>Third, guardrails should be simple. Schema validation, allow-lists, deny-lists, and deterministic postprocessing cover more real failures than elaborate "AI safety" layers. If you need hard guarantees, push critical decisions into code, not into another model call.</p>

<p>Fourth, cost controls need to be built in from the start. Set per-request token caps, per-tenant quotas, and model routing budgets. Otherwise every successful feature becomes a finance problem.</p>

<h2>What we'd actually recommend for a first production setup</h2>

<p>For most teams, a solid starting stack looks like this:</p>

<ul>
  <li><strong>Gateway:</strong> FastAPI or Go service with provider adapters.</li>
  <li><strong>Providers:</strong> one managed API provider plus one fallback.</li>
  <li><strong>Prompt management:</strong> Git-backed templates with version tags.</li>
  <li><strong>Validation:</strong> Pydantic or JSON Schema on every structured response.</li>
  <li><strong>Observability:</strong> OpenTelemetry, Prometheus, Tempo, and centralized logs.</li>
  <li><strong>RAG:</strong> PostgreSQL plus pgvector before adding more infrastructure.</li>
  <li><strong>Queueing:</strong> Celery, Sidekiq, or a cloud queue for long-running jobs.</li>
  <li><strong>Rate limiting:</strong> per user and per tenant at the gateway.</li>
</ul>

<p>Keep the synchronous path small. Put expensive enrichment, batch summarization, and offline indexing behind queues. Reserve real-time calls for interactions that truly need them.</p>

<h2>Next steps</h2>

<p>If your current setup is still direct model calls from app code, fix that first. Add a gateway, standardize request metadata, and make prompts versioned artifacts. Then build a small evaluation set for your top two use cases and require every prompt or model change to run against it.</p>

<p>After that, add output schema validation and tenant-level quotas. Only once those basics are in place should you spend time on advanced retrieval, agent frameworks, or self-hosted inference. Most teams get better results by tightening the platform around the model than by chasing a different model.</p>