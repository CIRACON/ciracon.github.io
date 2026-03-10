---
title: "LLM Production Best Practices for AI Engineering"
category: "AI Engineering"
description: "A practical guide to deploying, monitoring, and scaling large language models in production AI engineering systems."
date: "2026-03-10"
slug: "llm-production-best-practices-for-ai-engineering"
---

<p>Shipping an LLM demo is easy. Running LLM features in production is mostly an infrastructure and operations problem.</p>
<p>The model matters, but the hard parts usually show up elsewhere: request routing, latency budgets, prompt versioning, retrieval quality, rate limits, cost control, observability, and failure handling. If you already run APIs at scale, most of the playbook will look familiar. The difference is that LLM systems are probabilistic, expensive, and harder to test.</p>

<div class="diagram">
  <div class="diagram-title">Typical LLM Production Request Path</div>
  <div class="diagram-flow">
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">1</span>
        <span class="node-label">Client Request</span>
        <span class="node-sub">chat, search, agent task</span>
        <span class="node-tooltip">An incoming API call — chat completion, search query, or autonomous agent task — enters the system.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">2</span>
        <span class="node-label">Gateway</span>
        <span class="node-sub">auth, quotas, routing</span>
        <span class="node-tooltip">Handles authentication, rate limiting, and routes requests to the appropriate model or version.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">3</span>
        <span class="node-label">Orchestrator</span>
        <span class="node-sub">prompting, tools, retries</span>
        <span class="node-tooltip">Constructs prompts, manages tool calls and function routing, and handles retries on failures.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">4</span>
        <span class="node-label">Context Layer</span>
        <span class="node-sub">cache, vector DB, feature data</span>
        <span class="node-tooltip">Enriches the prompt with cached results, vector-retrieved context, and real-time feature data.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-node">
      <span class="node-num">5</span>
      <span class="node-label">Model Inference</span>
      <span class="node-sub">hosted API or self-hosted GPU</span>
      <span class="node-tooltip">The final LLM call — either a hosted API or self-hosted GPU endpoint — generates the response.</span>
    </div>
  </div>
  <div class="diagram-hint">Hover over each step for details</div>
</div>

<h2>Start with the service boundary, not the model</h2>
<p>A common mistake is letting every product team call a model provider directly. That works until you need consistent auth, usage tracking, prompt management, or a way to switch models without editing five services.</p>
<p>Put an internal LLM gateway in front of providers. It can be a small service in Go, Python, or Node, but it should do a few things reliably:</p>
<ul>
  <li>Authenticate callers with your existing platform identity.</li>
  <li>Apply per-team quotas and rate limits.</li>
  <li>Route requests by policy: cheapest model, fastest model, or approved model list.</li>
  <li>Attach tracing metadata and request IDs.</li>
  <li>Log prompts and responses with redaction rules.</li>
  <li>Support fallback providers when one API is degraded.</li>
</ul>
<p>We’ve seen teams use Kong, Envoy, or an internal FastAPI service for this layer. The exact tool matters less than having one choke point. Without it, every downstream app reimplements retries, timeouts, and provider-specific SDK logic badly.</p>

<h2>Design around latency and token budgets</h2>
<p>LLM production systems fail quietly when nobody owns latency and token budgets. A feature can look fine in staging and become unusable in production because retrieval adds 400 ms, prompt assembly adds another 150 ms, and the model takes 6 seconds to generate a long answer.</p>
<p>Set a budget per request path. For example:</p>
<ul>
  <li><strong>Interactive chat:</strong> p95 under 3 seconds for first token, under 10 seconds total.</li>
  <li><strong>Autocomplete:</strong> p95 under 500 ms.</li>
  <li><strong>Background enrichment:</strong> throughput matters more than tail latency.</li>
</ul>
<p>Then break that into components. Gateway 50 ms. Retrieval 200 ms. Reranking 150 ms. Model first token 1.5 seconds. Post-processing 100 ms. If the numbers do not fit, the architecture does not fit.</p>
<p>Token budgets matter just as much. Long prompts are expensive and slow. Put hard limits on:</p>
<ul>
  <li>System prompt size</li>
  <li>Retrieved context count</li>
  <li>Conversation history length</li>
  <li>Maximum output tokens</li>
</ul>
<p>Do not keep appending full chat history forever. Summarize old turns, keep structured state separately, and only send what the model needs for the current step.</p>

<h2>Treat prompts, tools, and retrieval as versioned artifacts</h2>
<p>Many teams version model names in code but leave prompts in string literals scattered across repositories. That becomes unmaintainable fast.</p>
<p>Store prompts in versioned files or a registry. Include metadata: owner, use case, model compatibility, expected input schema, and evaluation status. A simple setup using Git-backed YAML or JSON files works well:</p>
<ul>
  <li><code>prompt_id</code></li>
  <li><code>version</code></li>
  <li><code>template</code></li>
  <li><code>input_schema</code></li>
  <li><code>model_constraints</code></li>
  <li><code>eval_suite</code></li>
</ul>
<p>Do the same for tool definitions and retrieval pipelines. If your agent uses a SQL tool, a search tool, and a ticket API, those interfaces need versioning and tests just like any other dependency.</p>
<p>This is where LangChain, LlamaIndex, and DSPy can help, but we should be honest: they are useful for experimentation, not a substitute for platform discipline. In production, teams usually end up building thin internal abstractions with explicit schemas and fewer magic layers.</p>

<h2>RAG quality depends more on data plumbing than embeddings</h2>
<p>Retrieval-augmented generation usually breaks because the source documents are stale, chunking is poor, metadata is missing, or access control is ignored.</p>
<p>Focus on the ingestion pipeline first:</p>
<ul>
  <li>Normalize source documents into a stable internal format.</li>
  <li>Chunk by semantic boundaries, not fixed character counts alone.</li>
  <li>Attach metadata like tenant, document type, timestamp, and permissions.</li>
  <li>Re-embed incrementally when content changes.</li>
  <li>Keep a path back to source documents for citation and debugging.</li>
</ul>
<p>Vector databases like pgvector, Pinecone, Weaviate, and OpenSearch all work. For many teams, <code>Postgres + pgvector</code> is enough at first, especially if you already run Postgres well. Move to a dedicated vector store when scale, filtering, or operational isolation justifies it.</p>
<p>Add a reranker before the final context assembly if relevance matters. A bi-encoder retrieval step plus a cross-encoder reranker often beats trying a different embedding model every week.</p>

<h2>Build observability for prompts and outputs, not just infrastructure</h2>
<p>Standard API metrics are necessary but not enough. CPU, memory, and request counts will not tell you why answer quality dropped after a prompt change.</p>
<p>You need three layers of observability:</p>
<h3>Infrastructure metrics</h3>
<ul>
  <li>Request rate, error rate, latency, saturation</li>
  <li>GPU utilization, VRAM pressure, queue depth</li>
  <li>Provider API failures, timeout rates, retry counts</li>
</ul>
<h3>LLM application metrics</h3>
<ul>
  <li>Input tokens, output tokens, cost per request</li>
  <li>Cache hit rate</li>
  <li>Retrieval hit quality and document overlap</li>
  <li>Tool call success rate</li>
  <li>Fallback model usage</li>
</ul>
<h3>Quality signals</h3>
<ul>
  <li>User thumbs up or down</li>
  <li>Task completion rate</li>
  <li>Citation correctness</li>
  <li>Hallucination or policy violation flags</li>
</ul>
<p>OpenTelemetry is a good baseline for traces and metrics. Emit spans for retrieval, prompt rendering, model invocation, and tool execution. Products like Langfuse, Helicone, Phoenix, and Weights &amp; Biases can help with prompt traces and evals, but even if you use them, keep raw events in your own data platform.</p>

<h2>Use offline evals for safety and regression, online evals for reality</h2>
<p>LLM testing is not unit testing with fancier syntax. You need a mixed strategy.</p>
<p>Offline evals catch regressions before deploy. Build datasets from real traffic, sanitized and labeled where possible. Include hard cases: ambiguous questions, malformed inputs, prompt injection attempts, and low-context retrieval scenarios.</p>
<p>Check for things that matter to your product:</p>
<ul>
  <li>Correctness against reference answers</li>
  <li>Groundedness to retrieved context</li>
  <li>Structured output validity</li>
  <li>Policy compliance</li>
  <li>Tool selection accuracy</li>
</ul>
<p>Then run online evals in production. Shadow traffic, canary prompt versions, and compare quality signals by cohort. A prompt that scores well offline can still fail because users type differently than your eval set expected.</p>

<h2>Plan for failure modes up front</h2>
<p>Production LLM systems fail in more ways than normal APIs. Providers rate limit. Context retrieval returns nothing. The model emits invalid JSON. A tool call hangs. A safety filter blocks a legitimate request.</p>
<p>Handle these as first-class cases:</p>
<ul>
  <li>Set strict timeouts for every external dependency.</li>
  <li>Use circuit breakers around model providers and tools.</li>
  <li>Validate structured outputs with JSON Schema or Pydantic.</li>
  <li>Return degraded but useful responses when retrieval fails.</li>
  <li>Keep deterministic fallbacks for critical workflows.</li>
</ul>
<p>If the workflow updates a database, sends an email, or triggers an incident, do not let a free-form model response directly drive the action. Put a typed contract and policy checks in between.</p>

<h2>Decide early when to self-host models</h2>
<p>Most teams should start with hosted APIs. You move faster, avoid GPU operations, and get decent reliability. Self-hosting makes sense when one of these becomes dominant:</p>
<ul>
  <li>Data residency or compliance constraints</li>
  <li>Need for custom fine-tuned or open-weight models</li>
  <li>Very high request volume where hosted pricing is painful</li>
  <li>Need for low-level control over batching, quantization, or serving</li>
</ul>
<p>If you self-host, keep the serving stack boring. vLLM and TGI are common choices. Run them on Kubernetes only if your team already knows how to operate GPU node pools, autoscaling, and bin-packing. Otherwise, managed GPU instances with simple deployment automation are often the better first step.</p>
<p>Watch the operational details:</p>
<ul>
  <li>Model load time and warm pools</li>
  <li>KV cache behavior</li>
  <li>Continuous batching configuration</li>
  <li>GPU fragmentation and multi-tenant isolation</li>
  <li>Quantization trade-offs versus output quality</li>
</ul>

<h2>Control cost with routing, caching, and workload separation</h2>
<p>Cost overruns usually come from sending every task to the biggest model with full context. That is lazy architecture.</p>
<p>Use a routing policy. Small model for classification and extraction. Medium model for most chat. Large model only for hard cases or escalation. Cache aggressively where prompts are repeatable. Separate synchronous user-facing traffic from batch jobs so one does not starve the other.</p>
<p>At minimum, track cost by:</p>
<ul>
  <li>Team</li>
  <li>Feature</li>
  <li>Model</li>
  <li>Request type</li>
</ul>
<p>If you cannot attribute spend, you cannot optimize it.</p>

<h2>What usually works in practice</h2>
<p>A pragmatic production setup for many teams looks like this:</p>
<ul>
  <li>Internal LLM gateway for auth, quotas, routing, and logging</li>
  <li>Hosted model API first, self-host only when there is a clear reason</li>
  <li>RAG on Postgres plus pgvector before adding more moving parts</li>
  <li>Prompt and tool definitions stored in Git with versioned evals</li>
  <li>OpenTelemetry traces plus a prompt tracing tool</li>
  <li>Canary releases for prompt and model changes</li>
  <li>Schema validation around all structured outputs</li>
</ul>
<p>Next steps are straightforward. Map one production use case end to end. Define latency, token, and cost budgets. Put a gateway in front of model access. Version prompts and retrieval configs. Add traces around every step. Build a small eval set from real traffic before you tune anything else. That will get you farther than debating model benchmarks in a slide deck.</p>