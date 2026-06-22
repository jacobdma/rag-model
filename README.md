# IHI Assistant

Internal RAG assistant: hybrid local document search (BM25 + FAISS) with optional web augmentation. LLM served by a shared Ollama instance; FastAPI backend, Next.js frontend, MongoDB.

## Features

- Ingests `PDF`, `DOCX`, `PPTX`, `TXT`, `CSV` from shared drives
- Hybrid retrieval: BM25 + FAISS, small/large chunking
- LLM via shared Ollama (quantized Mistral-7B default) — prod and dev share one GPU model copy
- Live model/temperature/tone config from the frontend
- Optional Bing-compatible web search

## Stack

- **Backend:** FastAPI, Uvicorn, LangChain, FAISS, rank-bm25, sentence-transformers (bge embeddings)
- **LLM:** Ollama
- **Frontend:** Next.js, Tailwind CSS, lucide-react
- **Data:** MongoDB

## Prerequisites

- **Python 3.11**
- **Ollama** — serves the LLM (backend is an HTTP client, no in-process model). Install from https://ollama.com/download, then:
  ```
  ollama pull mistral:7b-instruct-q5_K_M
  ```
  Runs on `localhost:11434`. Override with `ollama_model` in config.yaml or `OLLAMA_MODEL`.
- **MongoDB** — local, default `mongodb://localhost:27017` (`start-dev.bat` launches one if not already running).

## Run — Native (dev)

Backend:
```
cd rag_model
python -m venv env
env\Scripts\activate.ps1
cd backend
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn scripts.main:app --host 0.0.0.0 --port 8000    # add --reload for dev
```
Frontend:
```
cd rag_model/frontend
npm install
npm run dev        # localhost:3000
```
Or just (from `rag_model/`):
```
start-dev.bat      # native dev stack on 8001/3001 (current branch), reload on
```

## Run — Docker (prod)

CPU-only containers built from `main` (LLM in host Ollama, embeddings on CPU — no GPU in the images). Prod and a native dev instance can run at once, sharing the host Ollama + MongoDB. Prod code is baked into the image, so branch-switching can't disturb it.

Host prerequisites (so containers can reach host services):
- Ollama: set `OLLAMA_HOST=0.0.0.0`.
- MongoDB: run `mongod --bind_ip_all`.

Deploy from main (guards a dirty tree, pulls, rebuilds, returns to your branch):
```
deploy.bat
```
Restart the last-built stack after a crash/reboot (no rebuild, no checkout):
```
start-prod.bat
```
Or Compose directly (repo root):
```
docker compose -p rag-prod up -d --build     # frontend :3000, backend :8000
docker compose -p rag-prod logs -f
docker compose -p rag-prod down
```
LAN access (bakes server IP into the frontend at build):
```
set HOST_IP=192.168.x.x
docker compose -p rag-prod up -d --build
```

## Configuration

### backend/config.yaml

| Key | Req | Description |
|-----|-----|-------------|
| `DOCUMENTS` | rec | Paths the pipeline can read |
| `MODEL_TOKEN` | yes | HuggingFace token (embedding downloads) |
| `mongo_uri` | yes | MongoDB URI |
| `ldap` | yes* | LDAP auth: `server`, `user`, `password`, `search_filter`, `base_dn` |
| `sharepoint` | yes* | On-prem SharePoint: `domain`, `user`, `password` |
| `BING_API_KEY` | opt | Bing-compatible search key |
| `IGNORE_FOLDERS` | opt | Paths under `DOCUMENTS` to skip |
| `IGNORE_KEYWORDS` | opt | Skip paths/files containing these |
| `ollama_host` | opt | Ollama URL (default `http://localhost:11434`) |
| `ollama_model` | opt | Model tag (default `mistral:7b-instruct-q5_K_M`) |
| `embed_device` | opt | bge device: `cpu` (default) or `cuda` (faster index builds) |

\* Will be made optional. Env overrides (used by Docker): `OLLAMA_HOST`, `OLLAMA_MODEL`, `EMBED_DEVICE`, `MONGO_URI`.

Example:
```yaml
DOCUMENTS:
  - /Users/User/SampleDocuments/
MODEL_TOKEN: my_model_token
mongo_uri: mongodb://localhost:27017
ollama_model: mistral:7b-instruct-q5_K_M
embed_device: cpu
BING_API_KEY: None
IGNORE_FOLDERS:
  - /Users/User/SkippedDocuments/
IGNORE_KEYWORDS:
  - skip
  - archive
ldap:
  server: "my_ldap_server"
  user: "my_ldap_user"
  password: "password"
  search_filter: "my_ldap_filter"
  base_dn: "my_ldap_base_dn"
sharepoint:
  domain: "sp_domain"
  user: "sp_user"
  password: "password"
```

### frontend/.env (native only; Docker uses build args)
```
NEXT_PUBLIC_HOST_IP=my_host_ip
NEXT_PUBLIC_BACKEND_PORT=8000
NEXT_PUBLIC_DOMAIN=my_email_domain
NEXT_PUBLIC_SERVER=my_email_server
```

## Project Structure

```
backend/scripts/
  chunk_documents.py     Document chunking
  config.py              Prompt templates, constants, ollama/env config
  file_readers.py        File parsing
  handler.py             Intent routing (math, code, general, ...)
  hybrid_retriever.py    BM25 + FAISS retrieval
  llm_utils.py           Ollama client
  load_utils.py          Share / document ingestion
  main.py                FastAPI app
  rag.py                 Pipeline
  retriever_builder.py   Builds / persists retrievers
  utils.py               Models

frontend/app/
  layout.tsx, page.tsx
  components/   chat, ContextWindow, DocumentUpload, Dropdown,
               LoginForm, SettingsMenu, Sidebar, Slider, Toggle
```

## License & Disclaimer

Third-party licenses in `NOTICE.txt` — preserve if redistributing. Provided "as-is" for internal use only; external or commercial deployment requires verifying all third-party license terms.

## Author

Jacob Ma — SWE Intern @ IHI, Summer 2025 — jma443@gatech.edu