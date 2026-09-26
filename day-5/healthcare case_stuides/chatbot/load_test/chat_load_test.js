import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '20s',
  thresholds: {
    http_req_duration: ['p(95)<3000'],
    http_req_failed: ['rate<0.05'],
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

export default function () {
  const question = QUESTIONS[Math.floor(Math.random() * QUESTIONS.length)];
  const res = http.post(
    `${BASE_URL}/chat`,
    JSON.stringify({ message: question, api_key: GROQ_API_KEY }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has answer field': (r) => JSON.parse(r.body).answer !== undefined,
  });
  sleep(1);
}
