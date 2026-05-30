# Transaction Chatbot — PoC

Take-home submission for the **AI Tech Lead** role.

A minimal working agent that lets bank customers check balances, browse transaction history, and ask about charges they don't recognise.

---

## Stack

- **LangGraph** — agent orchestration (ReAct-style: LLM → tool → LLM → respond)
- **Streamlit** — chat UI (one process, no separate frontend)
- **OpenAI-compatible LLM** — defaults to `gpt-4o-mini`, configurable via env
- **pandas + CSV** — stands in for the Core Banking API

The repo layout intentionally mirrors what would go into production:

```
.
├── data/transactions.csv      # demo data — 4 customers, ~45 transactions
├── src/
│   ├── app.py                 # Streamlit UI
│   ├── agent.py               # LangGraph graph definition
│   ├── tools.py               # @tool wrappers exposed to the agent
│   ├── data.py                # "core banking" — replace with real API in prod
│   └── guardrails.py          # input + output safety checks
├── tests/test_data.py         # sanity tests on the data layer
├── Dockerfile                 # for the Cloud Run / GKE deployment story
└── pyproject.toml
```

---

## Run it

### Option 1 — local Python

```bash
# 1. Install (Python 3.11+)
pip install -e .

# 2. Set your API key
export OPENAI_API_KEY=sk-...

# 3. Run
streamlit run src/app.py
```

Open http://localhost:8501 and pick a customer from the sidebar.

### Option 2 — Docker

```bash
docker build -t transaction-chatbot .
docker run --rm -p 8501:8501 -e OPENAI_API_KEY=sk-... transaction-chatbot
```

### Using a different LLM provider

The agent uses an OpenAI-compatible client. Point it at any compatible provider by setting `OPENAI_BASE_URL`:

```bash
# Groq (free tier, very fast)
export OPENAI_BASE_URL=https://api.groq.com/openai/v1
export OPENAI_API_KEY=gsk_...
export MODEL_NAME=llama-3.3-70b-versatile

# Local Ollama
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama   # ignored but required by the SDK
export MODEL_NAME=llama3.1
```

### Tests

```bash
pip install -e ".[dev]"
pytest tests/
```

---

## Demo scenarios

Each persona is shaped for a different conversation:

| Customer | Setup | Try asking |
|---|---|---|
| **Sarah Mitchell** (C001) | Typical professional with one mystery `SP* MERIDIAN CO` charge | *"Any charges I don't recognise?"* |
| **James Patel** (C002) | Student with a suspicious recurring `WWW.FITNESSPLUS24.IO` charge | *"What's that fitness charge?"* |
| **Eleanor Davies** (C003) | Three large `CRYPTO*BITX-LDN` charges — clear fraud demo | *"Show me my unfamiliar charges"* |
| **Mohammed Al-Rashid** (C004) | Two `SP* MERIDIAN CO` charges in the same month | *"How much did I spend on subscriptions?"* |

---

## What's in scope vs out

**In:** the three jobs from the brief — balance, transaction history, identifying unfamiliar charges. Read-only. Single agent, four tools, deterministic guardrails on input and output. Customer ID is passed into the system prompt to anchor every tool call.

**Out (deliberately, to fit 4 hours):**

- **Real auth.** Customer is picked from a dropdown; in production this would come from the authenticated mobile-app session (JWT in the header).
- **Persistent memory.** Conversation state lives only in the Streamlit session. The architecture diagram for GA adds Redis for multi-turn memory.
- **Real banking integration.** The CSV is the system-of-record. The `data.py` function signatures are the contract — swapping in a real core banking client is a one-file change.
- **Production guardrails.** The regex checks demonstrate the seam; a real deployment would use a managed guardrails service.
- **Eval harness.** Mentioned in the planning doc; not built here.
- **Observability.** No tracing or metric emission in the PoC. LangGraph traces would be enabled via LangSmith or OTel in production.
- **Containerised LLM.** Calls go straight to OpenAI; in production they'd go via the platform's egress proxy.

---

## Notable design choices

**The data layer is framework-agnostic.** `data.py` knows nothing about LangChain. Tools in `tools.py` are thin adapters. This makes the data layer trivially testable (see `tests/test_data.py`) and means swapping LangGraph for ADK later would only touch `agent.py` and `tools.py`.

**Customer ID is anchored in the system prompt, not passed by the user.** The agent reads `customer_id` from its own system message. The LLM cannot be tricked into looking up another customer's data, because the customer ID isn't user-controlled input.

**Tools are read-only.** No `transfer_money`, no `dispute_charge`. For MVP this keeps the blast radius of any LLM misbehaviour near zero. Write tools would be added in GA, behind step-up authentication and full audit logging.

**Heuristic-based "unfamiliar charges" detection.** For the PoC, `find_unfamiliar_charges` uses cryptic-prefix matching (`SP*`, `CRYPTO*`, `WWW.`). A real implementation would learn each customer's normal patterns and use an ML classifier — out of scope here, but the tool's interface stays the same.

**Single Streamlit process.** Fine for a PoC demo. The production architecture (see planning doc) has the agent behind FastAPI as a Cloud Run / GKE service, with the existing mobile app as the actual frontend.

---

## Trade-offs made to fit 4 hours

- Conversation history isn't persisted across page reloads.
- Guardrails are regex-based, not LLM-as-judge.
- No retries / circuit breakers on LLM failures — exceptions surface to the UI.
- No CI workflow in the repo (would be a single `pytest + ruff` GitHub Action in practice).
- No structured logging — `print`-level only.
- The Dockerfile pins versions in the install line rather than reading them from `pyproject.toml`. Pragmatic for a PoC; in production this would use the platform's standard base image and a proper dependency-locked install.

---

## How this would deploy at Lloyds

For a stakeholder demo before MVP: `gcloud run deploy --source .` — Cloud Run scales to zero so it costs nothing when idle.

For MVP (limited cohort) and beyond: the same container image targets the platform team's standard Kubernetes runtime, deployed via the Backstage-scaffolded GitHub Actions pipeline and Terraform module (see the planning document's architecture diagram).
