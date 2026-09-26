"""Application settings for agent_poc.

Reads from a `.env` file (if present) via pydantic-settings. Started as the
minimal slice needed by the conversation-memory subsystem (`agents/memory.py`,
`agents/llm.py`); now also carries the Neo4j/embedding/ingestion-source
settings from the base plan and Addendum 3 ("RAG Engine — Multi-Source
Ingestion & Retriever"), documented in `.env.example`. Later phases (source
clients, retriever, agent promotion) consume these but shouldn't need to add
new fields here beyond what's already listed in `.env.example`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Conversation memory & context trimming ---
    # Number of most-recent turns kept verbatim ("active" context). Valid
    # range per the plan is 8-10; default 10.
    MEMORY_ACTIVE_TURNS: int = 10

    # Fraction of the binding model context window reserved for the rolling
    # summary of older turns. Valid range per the plan is 0.12-0.15.
    MEMORY_SUMMARY_BUDGET_FRACTION: float = 0.15

    # Cheap model used for summary folding and query contextualization.
    MEMORY_SUMMARIZER_MODEL: str = "claude-haiku-4-5-20251001"

    # Max context window (tokens) per model, used to compute the summary
    # token budget. POC assumption — documented here rather than looked up
    # dynamically from the Anthropic API.
    MODEL_MAX_CONTEXT: dict[str, int] = {
        "claude-sonnet-5": 200_000,
        "claude-opus-5": 200_000,
        "claude-haiku-4-5-20251001": 200_000,
    }

    # --- Anthropic ---
    ANTHROPIC_API_KEY: str = ""

    # Optional override of the Anthropic API's base URL. Point this at a
    # local Anthropic-Messages-API-compatible proxy (e.g. LiteLLM, a
    # corporate gateway) to route every LLM call there instead of
    # api.anthropic.com. Left empty (default), the SDK uses its own default
    # endpoint. Wired into `agents/llm.py`'s client construction only.
    ANTHROPIC_BASE_URL: str = ""

    # Per-role model overrides (see plan's "Model / Embedding Choices" table).
    # `MEMORY_SUMMARIZER_MODEL` above already covers the memory-fold/query-
    # contextualization role; these cover Supervisor/sub-agents/synthesis.
    SUPERVISOR_MODEL: str = "claude-sonnet-5"
    SUBAGENT_MODEL: str = "claude-sonnet-5"
    SYNTHESIS_MODEL: str = "claude-opus-5"

    # --- Voyage AI embeddings ---
    VOYAGE_API_KEY: str = ""
    VOYAGE_EMBED_MODEL: str = "voyage-3.5"

    # --- Neo4j ---
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # --- PubMed / NCBI E-utilities ---
    NCBI_EMAIL: str = ""
    NCBI_API_KEY: str = ""

    # --- Demo seeding ---
    DEMO_TOPIC_QUERY: str = ""
    DEMO_MAX_RESULTS: int = 200

    # --- API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_BASE_URL: str = "http://localhost:8000"

    # --- Addendum 3: multi-source ingestion config ---

    # ChEMBL REST API, no key required.
    CHEMBL_BASE_URL: str = "https://www.ebi.ac.uk/chembl/api/data"

    # Path to a locally-downloaded DrugBank *open vocabulary* CSV (free,
    # license-free drug names/synonyms/external IDs only — NOT the licensed
    # DrugBank API/database). No sensible default; unset until the user
    # downloads the file and points this at it.
    DRUGBANK_VOCAB_PATH: str = ""

    # ClinicalTrials.gov REST API v2, no key required.
    CLINICALTRIALS_BASE_URL: str = "https://clinicaltrials.gov/api/v2"

    # OpenTargets GraphQL API, no key required.
    OPENTARGETS_GRAPHQL_URL: str = "https://api.platform.opentargets.org/api/v4/graphql"

    # --- OpenTelemetry ---

    # Opt-in: off by default so no exporter/background thread/network
    # activity happens (and no test mocking is needed) unless explicitly
    # enabled via .env.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "agentic-rag-poc"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "grpc"
    OTEL_METRICS_EXPORT_INTERVAL_MS: int = 15000


settings = Settings()
