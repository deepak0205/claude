# Graph Report - docs  (2026-09-26)

## Corpus Check
- Corpus is ~2,659 words - fits in a single context window. You may not need a graph.

## Summary
- 66 nodes · 78 edges · 8 communities
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 17 edges (avg confidence: 0.91)
- Token cost: 20,000 input · 116,360 output

## Community Hubs (Navigation)
- Elation Chart-Summary Architecture
- Banner Health Rollout
- Elation Impact Metrics
- Carta Healthcare on Bedrock
- Qualified Health Case Study
- Compliance & Pilot Phases
- Build Phases & Error Handling
- Commure Ambient AI Safety

## God Nodes (most connected - your core abstractions)
1. `Chart-Summary Service` - 14 edges
2. `Banner Health` - 7 edges
3. `Claude in Healthcare — 5 Case Studies` - 5 edges
4. `Per-Case-Study Structure` - 5 edges
5. `Carta Healthcare` - 5 edges
6. `Qualified Health` - 4 edges
7. `Elation Health` - 4 edges
8. `Commure` - 4 edges
9. `Distribution Model` - 4 edges
10. `Phase 0: Requirements & Compliance Sign-off` - 4 edges

## Surprising Connections (you probably didn't know these)
- `Banner Health` --shares_data_with--> `Banner Health`  [INFERRED]
  PLAN.md → claude-healthcare-case-studies.md
- `Summary Advisory, Not Authoritative` --semantically_similar_to--> `Constitutional AI`  [INFERRED] [semantically similar]
  elation-health-hld-lld.md → claude-healthcare-case-studies.md
- `Error Handling Table` --semantically_similar_to--> `Phase 1: Prompt & Data-Contract Prototyping`  [INFERRED] [semantically similar]
  elation-health-hld-lld.md → elation-health-development-plan.md
- `Carta Healthcare` --shares_data_with--> `Carta Healthcare`  [INFERRED]
  PLAN.md → claude-healthcare-case-studies.md
- `Banner Health` --shares_data_with--> `Banner Health`  [INFERRED]
  elation-health-hld-lld.md → claude-healthcare-case-studies.md

## Hyperedges (group relationships)
- **Documentation/Administrative Burden Reduction Mode** — backend_docs_claude_healthcare_case_studies_banner_health, backend_docs_claude_healthcare_case_studies_elation_health, backend_docs_claude_healthcare_case_studies_commure [EXTRACTED 1.00]
- **PHI Protection Pipeline (De-identification → Model Call → Audit)** — backend_docs_elation_health_hld_lld_chart_summary_service, backend_docs_elation_health_hld_lld_deidentification_boundary, backend_docs_elation_health_hld_lld_claude_api, backend_docs_elation_health_hld_lld_audit_logging [INFERRED 0.85]
- **Phased Specialty Rollout Pattern (mirrors Banner Health)** — backend_docs_elation_health_development_plan_phase_7, backend_docs_elation_health_hld_lld_rollout_plan, backend_docs_claude_healthcare_case_studies_banner_health [INFERRED 0.80]

## Communities (8 total, 0 thin omitted)

### Community 0 - "Elation Chart-Summary Architecture"
Cohesion: 0.14
Nodes (15): Audit & Logging, BAA Compliance, Caching Strategy, POST /internal/chart-summary/{patientId}, Chart-Summary Service, Claude API, De-identification Boundary, Elation Backend (+7 more)

### Community 1 - "Banner Health Rollout"
Cohesion: 0.18
Nodes (11): Claude in Healthcare — 5 Case Studies, Banner Health, Banner Health Case Study (claude.com), BannerWise, Claude Sonnet 4.5, Advancing Claude in Healthcare and the Life Sciences (Anthropic, 2026), Phase 7: Phased Rollout, Banner Health (+3 more)

### Community 2 - "Elation Impact Metrics"
Cohesion: 0.25
Nodes (8): 61% Chart-Review Time Reduction, Distribution Model, Elation Health, Elation Health Chart-Summary Development Plan, Elation Health × Claude HLD & LLD, Elation Health, Metrics to Track, Elation Health

### Community 3 - "Carta Healthcare on Bedrock"
Cohesion: 0.29
Nodes (8): Amazon Bedrock, Carta Healthcare, Carta Healthcare Case Study (claude.com), Lighthouse, Amazon Bedrock, Model Access Path: Bedrock over Direct API, Carta Healthcare, Carta Healthcare

### Community 4 - "Qualified Health Case Study"
Cohesion: 0.29
Nodes (7): Claude for Healthcare (Solutions Page), Qualified Health, University of Texas Medical Branch, University of Texas System, Banner Health, Per-Case-Study Structure, Qualified Health

### Community 5 - "Compliance & Pilot Phases"
Cohesion: 0.40
Nodes (6): BAA Compliance, Chart-Summary Service, Phase 0: Requirements & Compliance Sign-off, Phase 2: Chart-Summary Service Skeleton, Phase 6: Pilot, Prototype/Demo Scope Assumption

### Community 6 - "Build Phases & Error Handling"
Cohesion: 0.33
Nodes (6): Bedrock or Direct API Decision, Phase 1: Prompt & Data-Contract Prototyping, Phase 3: Claude Integration, Phase 4: Security & Audit Layer, Phase 5: Frontend Integration, Error Handling Table

### Community 7 - "Commure Ambient AI Safety"
Cohesion: 0.40
Nodes (5): Ambient AI, Commure, Constitutional AI, Summary Advisory, Not Authoritative, Commure

## Knowledge Gaps
- **17 isolated node(s):** `Elation Health Chart-Summary Development Plan`, `/graphify`, `Claude Sonnet 4.5`, `University of Texas System`, `University of Texas Medical Branch` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 21 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Chart-Summary Service` connect `Elation Chart-Summary Architecture` to `Compliance & Pilot Phases`, `Build Phases & Error Handling`, `Commure Ambient AI Safety`?**
  _High betweenness centrality (0.457) - this node is a cross-community bridge._
- **Why does `Banner Health` connect `Banner Health Rollout` to `Elation Impact Metrics`, `Qualified Health Case Study`, `Commure Ambient AI Safety`?**
  _High betweenness centrality (0.301) - this node is a cross-community bridge._
- **Why does `Constitutional AI` connect `Commure Ambient AI Safety` to `Banner Health Rollout`?**
  _High betweenness centrality (0.251) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Banner Health` (e.g. with `Banner Health` and `Banner Health`) actually correct?**
  _`Banner Health` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Carta Healthcare` (e.g. with `Carta Healthcare` and `Carta Healthcare`) actually correct?**
  _`Carta Healthcare` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Elation Health Chart-Summary Development Plan`, `/graphify`, `Claude Sonnet 4.5` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Elation Chart-Summary Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._