// k6 smoke test against GET /health.
//
// Cheap, CI-safe baseline: no LLM/Neo4j cost is incurred by /health itself
// beyond a single `RETURN 1` Neo4j round-trip, so this is safe to run at any
// time to confirm the API process is up before running the heavier
// query_load_test.js.
//
// Usage:
//   BASE_URL=http://localhost:8000 k6 run scripts/load_test/health_smoke_test.js

import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: 5,
  duration: "30s",
};

export default function () {
  const res = http.get(`${BASE_URL}/health`);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "body status is ok": (r) => {
      try {
        return r.json("status") === "ok";
      } catch (e) {
        return false;
      }
    },
  });
}
