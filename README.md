# IHI Assistant

## Table of Contents
* [Introduction](#introduction)
* [Features](#features)
* [Technologies](#technologies)
* [Getting started](#getting-started)
* [Configuration](#configuration)
* [Project Structure](#project-structure)
* [License Copies](#license-copies)
* [Disclaimer](#disclaimer)
* [Author](#author)

## Introduction

The IHI Assistant is a Retrieval-Augmented Generation (RAG) AI application for internal use. It uses both local document search and optional web augmentation to generate precise context-aware answers.

---

## Features

- Ingests documents from shared drives (`PDF`, `DOCX`, `PPTX`, `TXT`, `CSV`)
- Hybrid retrieval using **BM25 + FAISS** with small and large chunking strategies
- Frontend configuration for model, temperature, tone, reranking
- Optional web search via Bing-compatible API
- Local inference using `mistralai/Mistral-7B-Instruct-v0.1`
- Frontend built with **Next.js**, **Tailwind CSS**, and **Lucide Icons**

---

## Technologies

### Backend

- Core: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`
- RAG stack: `langchain`, `langchain-core`, `langchain-community`, `langchain-huggingface`, `langchain-text-splitters`
- Transformers + embeddings: `transformers`, `torch`, `sentence-transformers`, `faiss-cpu`, `rank-bm25`
- Parsing: `pdfplumber`, `pypdf`, `docx2txt`, `python-pptx`, `pandas`, `pillow`
- Utilities: `tqdm`, `requests`, `psutil`, `PyYAML`, `python-dotenv`, `regex`, `scikit-learn`, `scipy`, `sentence-transformers`, `threadpoolctl`

### Frontend

- `next`, `react`, `tailwindcss`
- `lucide-react` (icon set)
- Google Fonts: `Geist`, `Geist Mono`

---

## Getting Started

Note: This project is not hosted online. It is intended for local deployment on internal servers only.

### 1. Backend

_Requires Python 3.11_

```
# Navigate to the project directory
cd rag_model

# Set up virtual environment
python -m venv env
env\Scripts\activate.ps1

# Navigate to the backend directory
cd backend

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
python -m pip install -r requirements.txt

# Start the FastAPI server for local use
uvicorn scripts.main:app

# Start the FastAPI server for development
uvicorn scripts.main:app --reload

# Start the FastAPI server for LAN hosting
uvicorn scripts.main:app --host 0.0.0.0 --port 8000

# Access backend at localhost:8000/docs
```

### 2. Frontend
```
# Navigate to frontend directory

cd rag_model/frontend
npm install
npm run dev

# Access the app at localhost:3000

```

### NOTE

The app also contains ```start.bat```, ```frontend.bat```, and ```backend.bat``` files for development convenience. These can be run simply:
```
# Navigate to project directory
cd rag_model

# Example usage (start.bat will run both front- and backend)
start.bat

```

## Configuration

The assistant supports real-time adjustment of LLM parameters via the floating SettingsMenu:
- Model: Switch between supported Hugging Face models
- Temperature: Control generation creativity
- Tone: Choose between formal, neutral, casual
These are sent via `POST /set-config` to the FastAPI backend.

## Project Structure

```
/backend
├── scripts/
│   ├── chunk_documents.py          # Document chunking and processing
│   ├── config.py                   # Prompt templates & constants
│   ├── file_readers.py             # File reading functions
│   ├── handler.py                  # Routes queries by intent (math, code, general inquiry, etc)
│   ├── hybrid_retrievers.py        # Retrieves content based on hybrid retriever
│   ├── llm_utils.py                # Model loading and prompt handling
│   ├── load_utils.py               # Network share and document ingestion
│   ├── main.py                     # FastAPI app
│   ├── rag.py                      # Main pipeline logic
│   ├── retriever_builder.py        # Constructs and stores retrievers with persistance
│   └── utils.py                    # Models

/frontend
├── app/
│   ├── layout.tsx              # Global layout
│   ├── page.tsx                # Main chat page
│   ├──components/
│   │   ├── chat.tsx                # Message list + chat input
│   │   ├── ContextWindow.tsx       # Displays retrieved content
│   │   ├── DocumentUpload.tsx      # Document uploading window
│   │   ├── Dropdown.tsx            # Selection dropdown menu
│   │   ├── LoginForm.tsx           # Login form for LDAP authentication
│   │   ├── SettingsMenu.tsx        # Model configuration menu
│   │   ├── Sidebar.tsx             # Chat list + new chat
│   │   ├── Slider.tsx              # Sidebar slider component
│   │   └── Toggle.tsx              # Sidebar option toggle component


```

## Development Configuration

### config.yaml

Create file "config.yaml" inside of backend/

**DOCUMENTS** (recommended) will be all files the RAG Pipeline will have access to.

**BING_API_KEY** (optional) is the user or organization API Key for the Bing search API.

**MODEL_TOKEN** (required) is the user or organization HuggingFace token which enables model usage.

**IGNORE_FOLDERS** (optional) will be ignored paths inside of DOCUMENTS that the RAG Pipeline will not have access to.

**IGNORE_KEYWORDS** (optional) are a list of keywords that will be ignored if contained in the path or filename.

**ldap** (required, but will be made optional) is the LDAP configuration for your organization.
NOTE: **ldap** contains **server**, **user**, **password**, **search_filter**, and **base_dn** parameters. 
| Parameter      | Description                                      |
|----------------|--------------------------------------------------|
| server         | LDAP server hostname or URI (e.g. ldap://host)    |
| user           | DN or user principal for bind (cn=John,... )      |
| password       | Bind password                                     |
| search_filter  | RFC 4515 filter for selecting entries             |
| base_dn        | Starting DN for search (e.g. dc=example,dc=com)   |

Consult LDAP documentation for more information: https://ldap3.readthedocs.io/en/latest/

**mongo_uri** (required) is the mongo port for database access

**sharepoint** (required, but will be made optional) is the on-prem SharePoint credentials for organization file access.
NOTE: **sharepoint** contains **domain**, **user**, and **password** parameters.

#### config.yaml example:
```
DOCUMENTS:
  - /Users/User/SampleDocuments/

BING_API_KEY: None

MODEL_TOKEN: my_model_token

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

mongo_uri: mongodb://localhost:12345

sharepoint:
  domain: "sp_domain"
  user: "sp_user"
  password: "password"

```

### .env

Create file .env in frontend/

**NEXT_PUBLIC_HOST_IP** (required) is the IP of the hosting server.

This will look like:
```NEXT_PUBLIC_HOST_IP: my_host_ip```

## License Copies

A consolidated list of licenses for third-party libraries is provided in `NOTICE.txt`.

> You must preserve these notices and licenses if redistributing this project or using it in a commercial product.


## Disclaimer
This software is provided "as-is" and intended for internal use only. External distribution or commercial deployment requires verification of all third-party licensing terms.

## Author

Developed by Jacob Ma
SWE/ML Intern @ IHI, Summer 2025
Contact: jma443@gatech.edu