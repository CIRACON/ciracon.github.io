---
title: "Infrastructure as Code in AI Engineering"
category: "AI Engineering"
description: "Learn how Infrastructure as Code helps AI engineering teams automate, standardize, and scale reliable cloud environments."
date: "2026-04-21"
slug: "infrastructure-as-code-in-ai-engineering"
---

<p>Infrastructure as code matters more on AI platforms than it does on a plain web stack. The surface area is bigger: GPUs, object storage, model registries, vector databases, batch pipelines, feature stores, IAM sprawl, and usually three different ways to run inference because the first two were too expensive.</p>

<p>If you manage that with click-ops, you will lose. Not eventually. Immediately. The first time a team asks why staging can fine-tune a model but production cannot read from the artifact bucket, you will spend hours diffing consoles instead of shipping fixes.</p>

<p>The practical goal of IaC is simple: every environment should be reproducible, reviewable, and boring. For AI teams, that means the same Terraform plan should stand up your VPC, EKS cluster, S3 buckets, IAM roles for training jobs, KMS keys, observability stack, and the managed services around them. The less “special” infrastructure your ML platform has, the easier it is to operate.</p>

<div class="diagram">
  <div class="diagram-title">How IaC Should Flow in an AI Platform</div>
  <div class="diagram-flow">
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">1</span>
        <span class="node-label">Define modules</span>
        <span class="node-sub">Network, compute, IAM</span>
        <span class="node-tooltip">Build reusable Terraform modules for the platform primitives every team needs.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-step">
      <div class="diagram-flow-node">
        <span class="node-num">2</span>
        <span class="node-label">Promote via CI</span>
        <span class="node-sub">Plan, review, apply</span>
        <span class="node-tooltip">Use pull requests, policy checks, and environment promotion instead of manual console changes.</span>
      </div>
      <div class="diagram-flow-connector"><svg viewBox="0 0 32 12"><line x1="0" y1="6" x2="26" y2="6"/><polygon points="26,2 32,6 26,10"/></svg></div>
    </div>
    <div class="diagram-flow-node">
      <span class="node-num">3</span>
      <span class="node-label">Operate with drift control</span>
      <span class="node-sub">Audit, detect, recover</span>
      <span class="node-tooltip">Continuously detect drift, rotate credentials, and rebuild environments from code when needed.</span>
    </div>
  </div>
  <div class="diagram-hint">Hover over each step for details</div>
</div>

<h2>Use Terraform for cloud infrastructure, and keep Kubernetes manifests separate</h2>

<p>If we had to pick one default stack for most AI infrastructure teams today, it would be <code>Terraform</code> for cloud resources and either <code>Helm</code> or <code>Kustomize</code> for Kubernetes objects. Not Pulumi, not CloudFormation, not a giant shell script wrapped in CI.</p>

<p>Terraform wins because the ecosystem is still better. AWS, GCP, Azure, Datadog, Grafana, Snowflake, Confluent, Cloudflare, and most managed AI-adjacent services have usable providers. That matters more than language ergonomics.</p>

<p>We do <strong>not</strong> recommend putting every Kubernetes object into Terraform. Teams try this because they want “one tool for everything.” What they get is slow plans, ugly state, provider edge cases, and painful diffs on resources that change often. Keep Terraform focused on durable infrastructure:</p>

<ul>
  <li><code>VPC</code>, subnets, route tables, NAT, private endpoints</li>
  <li><code>EKS</code>/<code>GKE</code>/<code>AKS</code> clusters and node groups</li>
  <li><code>S3</code>/<code>GCS</code> buckets for datasets, artifacts, and logs</li>
  <li><code>IAM</code> roles, service accounts, workload identity bindings</li>
  <li><code>RDS</code>, Redis, OpenSearch, managed Kafka, secrets backends</li>
  <li><code>KMS</code>, audit logging, backup policies, DNS, certificates</li>
</ul>

<p>Then use Helm or Kustomize for the cluster layer: Argo Workflows, KServe, NVIDIA device plugin, External Secrets Operator, Prometheus, Istio, and your own inference services.</p>

<h2>Design modules around platform boundaries, not cloud products</h2>

<p>The biggest Terraform mistake we see is module design that mirrors the cloud console. A team creates one module for <code>aws_iam_role</code>, one for <code>aws_s3_bucket</code>, one for <code>aws_security_group</code>, and calls that reusable. It is not reusable. It just moves low-level complexity around.</p>

<p>Build modules around things your platform actually offers:</p>

<ul>
  <li><strong>Model training workspace</strong>: bucket access, queue permissions, GPU node pool access, secrets, monitoring</li>
  <li><strong>Online inference service</strong>: namespace, service account, autoscaling policy, model artifact access, ingress, dashboards</li>
  <li><strong>Data processing job</strong>: batch compute role, object storage paths, Spark config, metrics, alerting</li>
</ul>

<p>This gives application teams a higher-level interface. They should set a few inputs like <code>environment</code>, <code>team_name</code>, <code>artifact_bucket</code>, <code>gpu_enabled</code>, and maybe <code>allowed_data_domains</code>. They should not be composing IAM policy JSON by hand.</p>

<p>For AI platforms, IAM is where abstraction pays off. Most outages are permission bugs, not subnet bugs.</p>

<h2>Separate state aggressively</h2>

<p>Do not keep one Terraform state file for the whole platform. That works until the first high-risk apply touches networking, EKS, and monitoring in the same plan. Then your blast radius is the entire company.</p>

<p>We recommend splitting state into a few clear layers:</p>

<ul>
  <li><strong>Foundation</strong>: org-level IAM, DNS, shared KMS, audit logging</li>
  <li><strong>Network</strong>: VPC, subnets, gateways, private links</li>
  <li><strong>Cluster</strong>: EKS/GKE/AKS, node groups, base addons</li>
  <li><strong>Data services</strong>: databases, caches, Kafka, object storage</li>
  <li><strong>Environment apps</strong>: per-team or per-service resources</li>
</ul>

<p>Use remote state with locking. On AWS that usually means <code>S3</code> plus <code>DynamoDB</code> locking, unless you use Terraform Cloud. Keep apply permissions narrow. Your CI job for app infrastructure should not be able to rewrite shared networking.</p>

<p>This split also helps AI cost control. GPU node groups, vector databases, and training buckets should be isolated enough that you can tag them, report on them, and tear them down without touching the rest of the platform.</p>

<h2>Use GitOps for promotion, not manual applies from laptops</h2>

<p>Terraform from a developer laptop is fine for experiments. It is not fine for shared environments. We want all real changes to go through pull requests, plans in CI, policy checks, and controlled apply jobs.</p>

<p>A practical setup looks like this:</p>

<ul>
  <li><code>GitHub Actions</code> or <code>GitLab CI</code> runs <code>terraform fmt</code>, <code>validate</code>, <code>tflint</code>, and <code>tfsec</code></li>
  <li>PR comments include the plan output</li>
  <li><code>OPA</code> or <code>Sentinel</code> blocks bad patterns like public buckets or wildcard IAM</li>
  <li>Merge to <code>main</code> triggers apply for non-prod</li>
  <li>Production requires approval and uses a separate role</li>
</ul>

<p>For AI teams, add cost checks early. A bad Terraform change can create a GPU autoscaling group with the wrong instance family and burn a monthly budget in a day. We like <code>Infracost</code> in PRs because it catches obvious mistakes before apply.</p>

<h2>Treat secrets, identities, and data paths as first-class infrastructure</h2>

<p>On AI platforms, “infrastructure” is not just compute. It is also who can read which dataset, which service can pull which model, and how credentials are issued.</p>

<p>Our strong recommendation: avoid long-lived cloud keys entirely. Use workload identity. On AWS, use <code>IRSA</code> for EKS. On GCP, use Workload Identity. On Azure, use managed identities. Then wire secret delivery through something like <code>External Secrets Operator</code> backed by AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault.</p>

<p>This matters because AI systems move lots of sensitive data around. Training jobs read raw data. Inference services may access customer-specific embeddings. Batch pipelines write derived features. If those paths are not encoded in IAM and storage policy through IaC, they will drift into undocumented exceptions.</p>

<h2>What usually goes wrong</h2>

<p>Most IaC failures are not tooling failures. They are operating model failures.</p>

<ul>
  <li><strong>Too many modules, too early</strong>. Teams over-abstract before they understand usage patterns. Result: brittle modules nobody can change. Start with a few opinionated modules and refactor after repetition is obvious.</li>
  <li><strong>One state file for everything</strong>. This creates giant plans, lock contention, and scary rollbacks. Split state before the platform grows.</li>
  <li><strong>Console hotfixes during incidents</strong>. These fixes never get backported to code. Six weeks later, an apply reverts them and reintroduces the outage.</li>
  <li><strong>IAM managed as an afterthought</strong>. AI teams focus on clusters and GPUs, then discover training jobs cannot read artifacts or inference pods have broad admin access. Permission design should be part of the first platform iteration.</li>
  <li><strong>Mixing app delivery with infra delivery</strong>. Terraform should not redeploy your inference container because an environment variable changed. Keep infra cadence and app cadence separate.</li>
  <li><strong>No drift detection</strong>. If you never run scheduled plans or drift reports, your Terraform code becomes fiction.</li>
</ul>

<p>The worst pattern is shared “platform admin” access for everyone because IAM is hard. That works for a month. Then an engineer debugging a notebook accidentally deletes a queue, opens a security group, or bypasses the intended data boundary. Convenience turns into untraceable risk.</p>

<h2>Lessons learned from AI platform environments</h2>

<p>GPU infrastructure changes the usual IaC trade-offs. Capacity is constrained, quotas are fragile, and cloud APIs around accelerators are less forgiving than standard compute.</p>

<p>That means we recommend:</p>

<ul>
  <li>Managing GPU node pools as separate modules with explicit quotas and taints</li>
  <li>Encoding scheduling rules for training vs inference at the cluster layer, not in team docs</li>
  <li>Tagging every expensive resource with <code>team</code>, <code>project</code>, <code>environment</code>, and <code>cost_center</code></li>
  <li>Creating ephemeral environments only for the layers that need them; do not clone entire data planes for every branch</li>
</ul>

<p>We also learned that AI platforms need stronger teardown discipline than normal SaaS stacks. Idle notebooks, orphaned volumes, unattached load balancers, and forgotten vector indexes are common. If your IaC does not make destruction safe and routine, costs creep silently.</p>

<h2>What we would actually implement</h2>

<p>For a team building an internal AI platform on AWS today, we would keep it boring:</p>

<ul>
  <li><code>Terraform</code> with remote state in <code>S3</code> and locking in <code>DynamoDB</code></li>
  <li>A repo structure split by foundation, network, cluster, and service layers</li>
  <li><code>GitHub Actions</code> for plan/apply, with protected production workflows</li>
  <li><code>tflint</code>, <code>tfsec</code>, <code>Infracost</code>, and OPA checks in CI</li>
  <li><code>EKS</code> managed by Terraform, workloads delivered by <code>Helm</code> through Argo CD</li>
  <li><code>IRSA</code> and External Secrets Operator for identity and secrets</li>
  <li>Scheduled drift detection and monthly cleanup of unused resources</li>
</ul>

<p>That stack is not exciting. Good. Infrastructure should not be exciting.</p>

<h2>Next steps</h2>

<p>If your AI platform is still partly manual, start with three things this week:</p>

<ol>
  <li>Pick one environment and import its core resources into Terraform: network, cluster, buckets, IAM roles.</li>
  <li>Set up CI to run plan on every PR and block merges on failed validation or security checks.</li>
  <li>Ban console changes for shared environments unless they are incident-only and followed by a same-day code update.</li>
</ol>

<p>Then clean up state boundaries, standardize modules around platform use cases, and fix IAM before adding more services. Most teams do this in the opposite order. That is why their platform feels fragile even when the codebase looks “automated.”</p>