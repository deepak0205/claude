// k6 ramping-VUs load test against POST /query — the real end-to-end
// pipeline (Supervisor -> 7 sub-agents -> Evidence Synthesis), so each
// request triggers multiple real LLM calls (and, once seeded, real Neo4j
// retrieval). Thresholds are set generously to account for that cost.
//
// Sample queries are varied on purpose (epidemiology / target-mechanism /
// drug-safety / clinical-trial flavored) so the Supervisor's routing
// decision genuinely differs request to request, exercising all 7 agent
// nodes across a run rather than always taking the same path.
//
// Usage:
//   BASE_URL=http://localhost:8000 k6 run scripts/load_test/query_load_test.js
//
// SigNoz wiring: k6 has a built-in OpenTelemetry metrics output
// (`k6 run -o experimental-opentelemetry ...` as of the currently
// documented k6 CLI syntax — some k6 versions instead accept plain
// `-o opentelemetry`; verify against the installed `k6 version` before
// relying on this) that pushes k6's own run metrics (request duration, VU
// count, checks, iterations) as OTLP metrics to a collector endpoint. Point
// it at the same SigNoz OTel collector Addendum 4 stood up
// (`docker compose --profile observability up -d`, collector on
// localhost:4317) via the standard `OTEL_EXPORTER_OTLP_ENDPOINT` env var
// (or k6-specific `K6_OTEL_*` overrides, which take precedence), e.g.:
//
//   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
//     k6 run -o experimental-opentelemetry scripts/load_test/query_load_test.js
//
// so k6's load metrics land in the same SigNoz instance as the app's own
// traces/metrics.

import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const SAMPLE_QUERIES = [
  // epidemiology-flavored
  "What is the prevalence and incidence of EGFR-mutant lung cancer?",
  // target-mechanism-flavored
  "What is the role of EGFR mutations in lung cancer treatment resistance?",
  // drug-safety-flavored
  "What are the known adverse events and safety concerns of EGFR-targeted therapies?",
  // clinical-trial-flavored
  "What clinical trials are evaluating EGFR inhibitors for non-small cell lung cancer?",
  // competitive/molecule-flavored
  "Which molecules and companies are competing in the EGFR inhibitor market?",
];

export const options = {
  scenarios: {
    ramping_query_load: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "1m", target: 10 },
        { duration: "2m", target: 20 },
        { duration: "1m", target: 5 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<8000"],
  },
};

export default function () {
  const query = SAMPLE_QUERIES[Math.floor(Math.random() * SAMPLE_QUERIES.length)];

  const res = http.post(
    `${BASE_URL}/query`,
    JSON.stringify({ session_id: null, query }),
    { headers: { "Content-Type": "application/json" } }
  );

  check(res, {
    "status is 200": (r) => r.status === 200,
    "final_answer is non-empty": (r) => {
      try {
        const answer = r.json("final_answer");
        return typeof answer === "string" && answer.length > 0;
      } catch (e) {
        return false;
      }
    },
  });
}
