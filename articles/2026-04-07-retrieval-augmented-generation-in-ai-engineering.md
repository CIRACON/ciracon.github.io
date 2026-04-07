---
title: "Retrieval-Augmented Generation in AI Engineering"
category: "AI Engineering"
description: "Learn how retrieval-augmented generation improves AI systems by grounding responses in external data for better accuracy and relevance."
date: "2026-04-07"
slug: "retrieval-augmented-generation-in-ai-engineering"
---

<p>RAG is the default pattern when you need an LLM to answer questions over private or fast-changing data without fine-tuning for every document update. For platform teams, the hard part is not wiring up embeddings and a vector database. The hard part is building a system that stays correct after your corpus, prompts, models, and infrastructure all change underneath it.</p>

<p>My recommendation is simple: treat RAG like a retrieval system with an LLM attached, not like a prompt trick. The retrieval layer decides whether the model even has a chance to answer correctly. If that layer is weak, no amount of prompt tweaking will save you.</p>

<div class="diagram">
  <div class="diagram-title">Production RAG Request Flow</div>
  <div class="diagram-flow">
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">1</span>
        <span class="node-label">Ingest</span>
        <span class="node-sub">Parse and chunk</span>
        <span class="node-tooltip">Documents are cleaned, normalized, chunked, and tagged with metadata before indexing.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">2</span>
        <span class="node-label">Retrieve</span>
        <span class="node-sub">Hybrid search + rerank</span>
        <span class="node-tooltip">The system combines lexical and vector search, then reranks candidates before prompt assembly.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-node">
      <span class="node-num">3</span>
      <span class="node-label">Generate</span>
      <span class="node-sub">Grounded answer</span>
      <span class="node-tooltip">The LLM answers from retrieved context, ideally with citations and fallback behavior when evidence is weak.</span>
    </div>
  </div>
  <div class="diagram-hint">Hover over each step for details</div>
</div>

<h2>What a production RAG system actually needs</h2>

<p>A usable RAG stack has four parts: ingestion, indexing, retrieval, and evaluation. Most teams spend 80% of their energy on the first three and then wonder why the system drifts into nonsense after a few weeks. Evaluation is the part that keeps it honest.</p>

<p>For ingestion, we need deterministic document processing. That means stable chunking, metadata extraction, deduplication, and versioning. If you cannot answer <em>which source chunk produced this answer</em>, your debugging story is already broken.</p>

<p>For indexing, I would start with PostgreSQL plus <code>pgvector</code> if the corpus is modest and the team already knows Postgres. It is good enough for many internal knowledge bases and keeps operational complexity low. If you are dealing with tens of millions of chunks, aggressive filtering, or very high QPS, move to a purpose-built engine like OpenSearch, Weaviate, Qdrant, or Pinecone. My bias is to avoid adding a specialized vector store too early. Another stateful system is another thing to page on.</p>

<p>For retrieval, use hybrid search from day one. Dense retrieval alone misses exact identifiers, product names, error codes, and acronyms. BM25 alone misses semantic matches. Combining both gives better recall with very little extra complexity. OpenSearch does this well. Postgres can do a simpler version with full-text search plus vector similarity.</p>

<h2>How we would build it on a platform team</h2>

<p>A practical deployment looks like this:</p>

<ul>
  <li><strong>Storage:</strong> S3 or GCS for raw documents, Postgres or OpenSearch for indexed chunks.</li>
  <li><strong>Ingestion workers:</strong> Python services running on Kubernetes jobs, Celery workers, or Argo Workflows.</li>
  <li><strong>Embeddings:</strong> OpenAI text embedding models, Voyage, or a self-hosted model from Hugging Face via vLLM or Text Embeddings Inference.</li>
  <li><strong>Serving:</strong> A stateless API service that handles query rewriting, retrieval, reranking, prompt assembly, and response formatting.</li>
  <li><strong>Observability:</strong> OpenTelemetry traces, prompt and retrieval logs, token usage metrics, and an offline eval dataset in Git.</li>
</ul>

<p>Chunking matters more than teams think. I would start with 300 to 800 tokens per chunk with 10% to 20% overlap, then tune from actual failures. Tiny chunks improve recall but destroy coherence. Huge chunks bury the relevant sentence in noise and increase prompt cost. For API docs and runbooks, smaller chunks usually work better. For policy documents and design docs, larger chunks preserve context.</p>

<p>Metadata is not optional. Store source URL, document title, section heading, updated timestamp, access control labels, and document version. Good metadata lets you filter before similarity search and enforce authorization at retrieval time. If you skip this, you will eventually leak data across teams.</p>

<h2>Retrieval design choices that matter</h2>

<p>If you only take one recommendation from this article, make it this one: add reranking before you touch fancy agent patterns.</p>

<p>A basic retrieval pipeline should look like this:</p>

<ol>
  <li>Rewrite the user query if needed.</li>
  <li>Run hybrid retrieval for top 20 to 50 candidates.</li>
  <li>Rerank with a cross-encoder or API reranker.</li>
  <li>Select the top 5 to 10 chunks for the final prompt.</li>
</ol>

<p>Reranking is where a lot of quality gains come from. A cross-encoder model can compare the query and chunk together and sort candidates far better than raw vector distance. Cohere Rerank, Voyage rerankers, or open-source cross-encoders from Sentence Transformers are all reasonable options. Yes, it adds latency. It is usually worth it.</p>

<p>I would also recommend query rewriting for internal enterprise search. Users ask vague things like “why did deploys fail yesterday” when the real match contains “ArgoCD sync timeout in prod-eu-west-1.” A lightweight rewrite step can expand abbreviations, include synonyms, or normalize product names. Keep it constrained. Do not let the rewrite invent facts.</p>

<h2>Prompting and generation should stay boring</h2>

<p>The generation side should be conservative. Tell the model to answer only from provided context, cite sources, and say it does not know when evidence is weak. This sounds obvious, but many teams still ask the model to be “helpful” and then act surprised when it fills gaps with plausible nonsense.</p>

<p>I prefer prompts that separate instructions, user question, and retrieved context clearly. Keep the final prompt deterministic and inspectable. Store prompt templates in version control. Changing prompt text in a dashboard with no review process is a good way to create outages nobody can reproduce.</p>

<p>For many internal tools, a small or mid-sized model with strong retrieval beats a larger model with weak retrieval. If the context is right, generation is easy. If the context is wrong, the biggest model in the world still gives you a polished bad answer.</p>

<h2>What usually goes wrong</h2>

<p>Most production RAG systems fail for boring reasons.</p>

<ul>
  <li><strong>Bad chunking:</strong> Tables, code blocks, and headings get split incorrectly, so retrieval returns fragments with no meaning.</li>
  <li><strong>No document lifecycle:</strong> Old versions stay indexed, deleted files remain searchable, and answers cite stale content.</li>
  <li><strong>Vector-only retrieval:</strong> Error codes, SKUs, and exact config names disappear because lexical search was skipped.</li>
  <li><strong>No evaluation loop:</strong> Teams optimize embedding models and vector indexes without measuring answer quality on a fixed test set.</li>
  <li><strong>Missing access controls:</strong> Retrieval ignores document permissions and exposes content across tenants or teams.</li>
  <li><strong>Prompt stuffing:</strong> Too many chunks get shoved into context, which increases cost and lowers answer quality.</li>
</ul>

<p>The worst mistake I see is treating retrieval failures like model failures. If the answer is wrong, first inspect the retrieved chunks. In many cases the model never saw the right information. Debugging prompts before checking retrieval is wasted effort.</p>

<h2>How to evaluate RAG without fooling yourself</h2>

<p>You need an offline eval set before launch. Not later. Before launch.</p>

<p>Build 100 to 300 representative questions from real support tickets, internal docs queries, and known hard cases. For each question, store expected source documents or acceptable answers. Then measure:</p>

<ul>
  <li><strong>Retrieval recall:</strong> did the top-k results contain the right chunk?</li>
  <li><strong>Answer groundedness:</strong> did the answer stay within retrieved evidence?</li>
  <li><strong>Citation accuracy:</strong> do cited sources actually support the claim?</li>
  <li><strong>Latency and cost:</strong> p50 and p95 across retrieval and generation.</li>
</ul>

<p>I would not rely only on LLM-as-judge scoring. It is useful, but it drifts and can miss domain-specific mistakes. Pair automated scoring with a small human-reviewed benchmark. Keep failed examples and rerun them on every retrieval, prompt, or model change through CI.</p>

<h2>Infrastructure recommendations for reliability</h2>

<p>RAG services are infrastructure-heavy in a way many app teams underestimate. Embedding jobs spike CPU and network. OCR pipelines fail on malformed PDFs. Vector indexes need rebuild strategies. LLM APIs rate-limit at the worst possible time.</p>

<p>Use queues between ingestion stages. Make every stage idempotent. Store chunk hashes so reprocessing does not duplicate embeddings. Version your embedding model and index schema so you can rebuild cleanly. If you change chunking strategy or embedding model, plan a full reindex. Partial migrations create mixed-quality retrieval that is painful to diagnose.</p>

<p>On Kubernetes, separate ingestion workers from query-serving pods. They have different scaling patterns. Serving paths want low latency and predictable memory. Ingestion paths want throughput and can tolerate retries. Mixing them on the same deployment is how you get noisy-neighbor incidents.</p>

<h2>Lessons learned from real deployments</h2>

<p>The biggest lesson is that retrieval quality beats model sophistication for most internal use cases. Teams love to jump to multi-agent workflows, tool orchestration, and long-context models. Usually they just need cleaner documents, better chunking, hybrid search, and reranking.</p>

<p>The second lesson is that stale data kills trust faster than occasional “I don’t know” responses. If your assistant answers confidently from last quarter’s runbook, users stop trusting it. Freshness pipelines and source citations matter more than conversational polish.</p>

<p>The third lesson is that platform ownership matters. RAG touches storage, indexing, model APIs, IAM, observability, and application UX. If nobody owns the whole path end to end, failures get bounced between teams and never really get fixed.</p>

<h2>What I would recommend starting with</h2>

<p>If you are building your first internal RAG service, keep it simple:</p>

<ol>
  <li>Use S3 or GCS for source docs.</li>
  <li>Use Postgres plus <code>pgvector</code> unless scale clearly forces something else.</li>
  <li>Implement hybrid retrieval and reranking immediately.</li>
  <li>Store rich metadata and enforce ACL filtering in retrieval.</li>
  <li>Build an offline eval set before broad rollout.</li>
  <li>Return citations in every answer.</li>
  <li>Log retrieved chunks and prompt versions for debugging.</li>
</ol>

<p>Then run it with a small set of users, collect failed queries, and improve retrieval before swapping models. That is the path that usually works. The teams that skip evaluation and chase model upgrades first usually end up with a more expensive system that is still wrong.</p>