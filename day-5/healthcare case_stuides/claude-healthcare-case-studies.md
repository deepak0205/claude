# Claude in Healthcare — 5 Case Studies

Source: [Claude for Healthcare](https://claude.com/solutions/healthcare), individual customer pages linked below, and [Advancing Claude in healthcare and the life sciences](https://www.anthropic.com/news/healthcare-life-sciences) (Anthropic, 2026).

---

## 1. Banner Health — Reducing Physician Burnout at Scale

- **Company / Product:** Banner Health, one of the largest nonprofit hospital systems in the US. Built **BannerWise**, a Claude Sonnet 4.5-powered enterprise AI platform.
- **Problem:** Physician burnout driven by documentation and administrative burden across a large multi-state health system.
- **Solution:** BannerWise drafts documentation and summarizes patient records; rolled out to 55,000+ employees across hospitals and medical offices in six states. Chart-prep capabilities are expanding into neurology, cardiology, and infectious disease, with a broader rollout planned. An automation agent is also in development to streamline workflows further.
- **Outcome / Metrics:** 85% of users reported meaningful time savings.
- **Why it matters:** Banner's CTO cited Anthropic's safety focus and Constitutional AI approach as the deciding factor in vendor choice — signals that trust/safety framing, not just capability, is winning enterprise healthcare deals. Planned expansion into customer experience, revenue cycle, and supply chain shows a single platform scaling across non-clinical operations too.
- **Source:** [Banner Health case study](https://claude.com/customers/banner-health)

---

## 2. Qualified Health — Identifying Patients for Life-Saving Treatments

- **Company / Product:** Qualified Health, in partnership with the University of Texas System.
- **Problem:** Fragmented medical records make it hard to systematically identify patients eligible for evidence-based interventions at population scale.
- **Solution:** Claude-built protocols screen patient populations against fragmented records to surface eligible candidates.
- **Outcome / Metrics:** Screening deployed across a patient population of **1M+** at the University of Texas Medical Branch.
- **Why it matters:** Demonstrates Claude operating at population-health scale (not just per-patient), and as an intermediary layer that works across fragmented, multi-source medical records rather than requiring a single unified EHR.
- **Source:** [Claude for Healthcare](https://claude.com/solutions/healthcare)

---

## 3. Carta Healthcare — 66% Faster Clinical Data Processing

- **Company / Product:** Carta Healthcare's **Lighthouse** platform, deployed via Amazon Bedrock.
- **Problem:** Clinical registry abstraction — extracting and structuring data from patient medical records — is slow and manual, spanning both structured and unstructured data.
- **Solution:** Claude serves as the AI engine for clinical registry abstraction inside Lighthouse, semantically interpreting structured and unstructured medical data and using clinical context to formulate answers.
- **Outcome / Metrics:** **66% faster** clinical data processing while maintaining **99% accuracy**.
- **Why it matters:** Carta's CTO framed this as a "complete re-invention of understanding a patient's medical record," and highlighted Bedrock as enabling rapid, secure deployment of new Claude models — a template for regulated-industry deployment via cloud model marketplaces.
- **Source:** [Carta Healthcare case study](https://claude.com/customers/carta-healthcare)

---

## 4. Elation Health — 61% Less Time on Chart Review

- **Company / Product:** Elation Health, a primary-care EHR platform.
- **Problem:** Chart review and documentation consume clinician time that should go to patients.
- **Solution:** Claude embedded directly into the EHR platform to reduce chart-review and documentation burden for primary-care clinicians.
- **Outcome / Metrics:** **61% less time** spent on chart review.
- **Why it matters:** Elation building Claude directly into its own EHR product (rather than via a hospital-system integration layer) reflects Anthropic's current healthcare distribution model — going through health-tech vendors — contrasted with competitors partnering directly with dominant EHR incumbents.

---

## 5. Commure — Clinical Documentation Automation at Scale

- **Company / Product:** Commure's **Ambient AI** product.
- **Problem:** Automating clinical documentation directly from patient encounters requires very high precision — errors at scale (tens of millions of appointments) erode clinician trust quickly.
- **Solution:** Claude's model suite powers ambient documentation generation from patient encounters.
- **Outcome / Metrics:** Saving clinicians **millions of hours** annually, according to Commure.
- **Why it matters:** Commure's CTO framed precision as "the prerequisite for trust" — this case study is the clearest articulation of why accuracy, not just automation, is the binding constraint for ambient clinical AI at scale.

---

## Cross-cutting takeaways

- **Distribution model:** Anthropic's healthcare reach currently runs through health-tech vendors (Elation, Commure, Carta) and health systems building on the API (Banner) rather than a single EHR-incumbent partnership — a contrast to OpenAI's Microsoft/Epic route.
- **Two work modes:** documentation/administrative burden reduction (Banner, Elation, Commure) vs. structured data extraction/screening at population scale (Carta, Qualified Health).
- **Timing:** These case studies were published around August 2026, alongside a ~$965B valuation and reported IPO preparation — likely intended to substantiate enterprise traction claims.

Sources:
- [Healthcare | Claude by Anthropic](https://claude.com/solutions/healthcare)
- [Banner Health Claude Platform (API) case study](https://claude.com/customers/banner-health)
- [Customer story | Carta Healthcare | Claude](https://claude.com/customers/carta-healthcare)
- [Advancing Claude in healthcare and the life sciences \ Anthropic](https://www.anthropic.com/news/healthcare-life-sciences)
