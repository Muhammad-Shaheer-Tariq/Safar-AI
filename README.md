# SafarAI AI Travel Agent

SafarAI is a Streamlit and FastAPI travel assistant that combines a stateful LangGraph agent with live weather, currency conversion, local restaurant and attraction data, travel-policy retrieval, itinerary planning, and PKR budget tracking.

## Features

- AI travel assistant for planning, recommendations, policies, restaurants, attractions, weather, budget, and itinerary actions.
- ChromaDB RAG search for travel policies and etiquette.
- CSV-backed restaurant and attraction search.
- Open-Meteo weather lookup.
- Frankfurter currency conversion with a public fallback for currencies not covered by Frankfurter.
- Backend-owned budget and manual expense tracking.
- Prompt-injection and travel-scope protection before LangGraph execution.

## Architecture

```text
Streamlit frontend -> FastAPI -> Pydantic validation -> security guard
	-> LangGraph -> Groq LLM -> validated tools -> MemorySaver state -> response
```

The frontend has exactly four areas: AI Assistant, Budget Tracker, Weather, and Currency Converter. Restaurants, policies, attractions, and itinerary actions remain inside the assistant.

## Tech Stack

- Python 3.11
- Streamlit
- FastAPI and Uvicorn
- LangGraph, LangChain, and Groq
- Pydantic v2
- ChromaDB, HuggingFace embeddings, and sentence-transformers
- Pandas and Requests
- Docker Compose

## Project Structure

```text
backend/app/main.py              FastAPI endpoints and request validation
backend/app/agent/               LangGraph state, prompts, tools, and reducers
backend/app/security/            Prompt-injection and scope guard
backend/scripts/ingest_data.py   Policy ingestion into ChromaDB
frontend/app.py                  Streamlit welcome page and four-tab UI
data/                             Source CSV/TXT data and processed index
docker-compose.yaml              Backend/frontend deployment
```

## Environment

Copy `.env.example` to `.env` and set `GROQ_API_KEY`. Keep `.env` private and never commit real credentials. `N8N_WEBHOOK_URL` is optional and is used only for itinerary export.

## Local Development

From the repository root, install backend dependencies and start the API:

```bash
python3 -m pip install -r backend/requirements.txt
PYTHONPATH=backend python3 -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
python3 -m pip install -r frontend/requirements.txt
cd frontend
BACKEND_URL=http://localhost:8000 streamlit run app.py
```

Open `http://localhost:8501`.

## Usage

Use the AI Assistant for travel questions and itinerary actions. Set the starting budget in Budget Tracker, then record manual expenses with a description, category, and PKR amount. Weather and Currency Converter use the dedicated live backend endpoints.

Policy data can be rebuilt with:

```bash
PYTHONPATH=backend python3 backend/scripts/ingest_data.py
```

## Security

Chat requests are validated by Pydantic and checked before state mutation or agent invocation. The guard rejects prompt extraction, role override, secret/state disclosure, arbitrary tool manipulation, and clearly unrelated requests. Retrieved documents and tool responses are reference data only and cannot override system instructions.

## Testing

Run syntax and security checks:

```bash
python3 -m py_compile frontend/app.py backend/app/main.py backend/app/security/prompt_guard.py
PYTHONPATH=backend python3 -m unittest backend/app/security/tests.py
```

Useful endpoint checks include `GET /health`, `POST /api/weather`, `POST /api/currency`, `PATCH /api/state/{thread_id}/budget`, and `POST /api/state/{thread_id}/expenses`.

## Docker Deployment

```bash
docker compose build
docker compose up
```

The frontend is available at `http://localhost:8501` and the backend at `http://localhost:8000`. Stop the stack with `docker compose down`. The backend health check gates frontend startup.

## Troubleshooting

- If chat is unavailable, verify `GROQ_API_KEY` and backend logs.
- If policy search returns no results, rebuild the Chroma index and confirm `data/processed/chroma_db` exists.
- If the frontend cannot reach the API locally, confirm `BACKEND_URL=http://localhost:8000`.
- `MemorySaver` is process-local; conversation state is lost when the backend process restarts and is not shared across replicas. Use a persistent LangGraph checkpointer before multi-worker production deployment.

## License

No license file is currently included in this repository.
