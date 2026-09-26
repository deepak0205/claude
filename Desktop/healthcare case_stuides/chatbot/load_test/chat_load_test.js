import http from 'k6/http';
import { check, sleep } from 'k6';

// Ramp 0 -> 10 -> 40 concurrent virtual users to actually exercise the
// per-session/registry locking in backend/main.py, not just a flat trickle.
export const options = {
  stages: [
    { duration: '15s', target: 10 },
    { duration: '20s', target: 40 },
    { duration: '20s', target: 40 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<3000', 'p(99)<6000'],
    http_req_failed: ['rate<0.05'],
    checks: ['rate>0.95'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const GROQ_API_KEY = __ENV.GROQ_API_KEY || '';

const QUESTIONS = [
  'What did Carta Healthcare achieve with Claude?',
  'How is Banner Health using Claude?',
  'What population does Qualified Health screen?',
  'How much time does Elation Health save on chart review?',
  'What does Commure automate with Claude?',
];

// Module scope: each k6 VU gets its own isolated JS runtime, so this is
// automatically a distinct, persistent session id per virtual user across
// that VU's iterations — first call sends null, backend mints one, every
// later call from this VU reuses it. No uuid dependency needed.
let sessionId = null;

export default function () {
  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(
    `${BASE_URL}/chat`,
    JSON.stringify({ message: question, session_id: sessionId, api_key: GROQ_API_KEY }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'has answer field': (r) => {
      try {
        return JSON.parse(r.body).answer !== undefined;
      } catch (e) {
        return false;
      }
    },
    'has session_id field': (r) => {
      try {
        return JSON.parse(r.body).session_id !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  if (ok && res.status === 200) {
    try {
      sessionId = JSON.parse(res.body).session_id;
    } catch (e) {
      // leave sessionId as-is; next iteration retries with null
    }
  }

  sleep(1);
}

// NOTE: running 40 VUs against a REAL Groq key may surface Groq's own rate
// limits as http_req_failed — that's Groq throttling, not a bug in this
// app's concurrency handling. For a real-key run, tune `target` down (e.g.
// 5-10), or monkeypatch ChatAgent.answer to a fast stub server to load-test
// the locking path in isolation. See specs/SPEC.md "Load testing" section.
