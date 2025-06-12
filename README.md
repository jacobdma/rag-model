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
```

### 2. Frontend
```
# Inside the /frontend directory
cd rag_model/frontend
npm install
npm run dev

# Access the app at http://localhost:3000

```

## Configuration

The assistant supports real-time adjustment of LLM parameters via the floating SettingsMenu:
- Model: Switch between supported Hugging Face models
- Temperature: Control generation creativity
- LLM Reranking: Toggle slow but more accurate reranking
- Tone: Choose between formal, neutral, casual
These are sent via `POST /set-config` to the FastAPI backend.

## Project Structure

```
/backend
├── scripts/
│   ├── chunk_documents.py          # Chunks documents in parallel
│   ├── config.py                   # Prompt templates & constants
│   ├── file_readers.py             # File reading functions
│   ├── hybrid_retrievers.py        # Retrieves content based on hybrid retriever
│   ├── llm_utils.py                # Model loading and prompt handling
│   ├── load_utils.py               # Network share and document ingestion
│   ├── main.py                     # FastAPI app
│   ├── rag.py                      # Main pipeline logic
│   └── retriever_builder.py        # Constructs and stores retrievers with persistance

/frontend
├── app/
│   ├── layout.tsx              # Global layout
│   ├── page.tsx                # Main chat page
│   ├──components/
│   │   ├── chat.tsx                # Message list + chat input
│   │   ├── Dropdown.tsx            # Selection dropdown menu
│   │   ├── SettingsMenu.tsx        # Model configuration menu
│   │   └── Sidebar.tsx             # Chat list + new chat

```

## License Copies

A consolidated list of licenses for third-party libraries is provided in `NOTICE.txt`.

> You must preserve these notices and licenses if redistributing this project or using it in a commercial product.


## Disclaimer
This software is provided "as-is" and intended for internal use only. External distribution or commercial deployment requires verification of all third-party licensing terms.

## Author

Developed by Jacob Ma
Machine Learning Intern @ IHI, Summer 2025
Contact: jacobdma218@gmail.com