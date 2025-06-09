# IHI Assistant

## Table of Contents
* [Introduction](#introduction)
* [Features](#features)
* [Technologies](#technologies)
* [Getting started](#getting-started)
* [Configuration](#configuration)
* [Project Structure](#project-structure)
* [Licensing & Attribution](#licensing---attribution)
* [License Copies](#license-copies)
* [Disclaimer](#disclaimer)
* [Author](#author)

## Introduction

The IHI Assistant is a Retrieval-Augmented Generation (RAG) AI application for internal use. It uses both local document search and optional web augmentation to generate precise context-aware answers.

---

## Features

- Ingests documents from shared drives (`PDF`, `DOCX`, `PPTX`, `TXT`, `CSV`)
- Hybrid retrieval using **BM25 + FAISS** with chunking strategies
- Query enrichment via **reformulation + diversification**
- Frontend configuration for model, temperature, tone, reranking
- Optional web search via Bing-compatible API
- Local inference using `mistralai/Mistral-7B-Instruct-v0.1` and Hugging Face Transformers
- Frontend built with **Next.js**, **Tailwind CSS**, and **Lucide Icons**

---

## Technologies

### Backend

- `fastapi`, `uvicorn`, `pydantic`
- `langchain`, `langchain-core`, `langchain-community`, `langchain-huggingface`
- `transformers`, `torch`, `sentence-transformers`
- `faiss-cpu`, `tqdm`, `requests`
- `pdfplumber`, `docx2txt`, `python-pptx`, `pandas`

### Frontend

- `next`, `react`, `tailwindcss`
- `lucide-react` (icon set)
- Google Fonts: `Geist`, `Geist Mono`

---

## Getting Started

Note: This project is not hosted on a remote Git repository. It is intended for local deployment on internal servers only.

### 1. Backend

```
# Navigate to the backend directory
cd /rag_model/backend

# Set up virtual environment and install dependencies
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload

```

### 2. Frontend
```
# Inside the /frontend directory
cd /rag_model/frontend
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
- Autoscroll: Keep chat view pinned to the latest message
These are sent via `POST /set-config` to the FastAPI backend.

## Project Structure

```
/backend
├── app/
│   ├── config.py                   # Prompt templates & constants
│   ├── llm_utils.py                # Model loading and prompt handling
│   ├── load_utils.py               # Network share and document ingestion
│   ├── main.py                     # FastAPI app
│   ├── rag.py                      # Main pipeline logic
│   ├── retrieve_utils.py           # Retrieval logic with BM25 and FAISS
│   ├── utils.py                    # Document splitting, embedding, reranking

/frontend
├── app/
│   ├── page.tsx                # Main chat page
│   ├── layout.tsx              # Global layout
│   ├──components/
│   │   ├── chat.tsx                # Message list + chat input
│   │   └── settings_menu.tsx       # Model controls
```

## Licensing & Attribution

This project uses the following third-party libraries, frameworks, models, and fonts. All are compatible with commercial use under open-source licenses.

---

### Backend Libraries

| Component                            | License        | Source |
|-------------------------------------|----------------|--------|
| `transformers`                      | Apache 2.0     | https://github.com/huggingface/transformers  
| `torch`                             | BSD 3-Clause   | https://github.com/pytorch/pytorch  
| `sentence-transformers`             | Apache 2.0     | https://github.com/UKPLab/sentence-transformers  
| `langchain`, `langchain-core`       | MIT            | https://github.com/langchain-ai/langchain  
| `langchain-community`, `langchain-huggingface`, `langchain-text-splitters` | MIT | https://github.com/langchain-ai/langchain  
| `faiss-cpu`                         | MIT            | https://github.com/facebookresearch/faiss  
| `tqdm`                              | MPL 2.0        | https://github.com/tqdm/tqdm  
| `requests`                          | Apache 2.0     | https://github.com/psf/requests  
| `pydantic`                          | MIT / Apache 2.0 | https://github.com/pydantic/pydantic  
| `uvicorn`                           | BSD 3-Clause   | https://github.com/encode/uvicorn  
| `pdfplumber`                        | MIT            | https://github.com/jsvine/pdfplumber  
| `python-pptx`                       | MIT            | https://github.com/scanny/python-pptx  
| `docx2txt`                          | MIT            | https://github.com/ankushshah89/python-docx2txt  
| `pandas`                            | BSD 3-Clause   | https://github.com/pandas-dev/pandas  

---

### Models Used

| Model Name                           | License        | Source |
|--------------------------------------|----------------|--------|
| `mistralai/Mistral-7B-Instruct-v0.1` | Apache 2.0     | https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.1  
| `BAAI/bge-large-en-v1.5`             | Apache 2.0     | https://huggingface.co/BAAI/bge-large-en-v1.5  
| `intfloat/e5-large-v2`               | Apache 2.0     | https://huggingface.co/intfloat/e5-large-v2  
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Apache 2.0   | https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2

---

### Frontend Libraries

| Component         | License        | Source |
|------------------|----------------|--------|
| `next`           | MIT            | https://github.com/vercel/next.js  
| `react`          | MIT            | https://github.com/facebook/react  
| `tailwindcss`    | MIT            | https://github.com/tailwindlabs/tailwindcss  
| `lucide-react`   | ISC            | https://github.com/lucide-icons/lucide  
| `Geist` fonts    | Open Font License | https://vercel.com/fonts  

---

## License Copies

All license texts are included in the `LICENSES/` directory. A consolidated list of notices is provided in `NOTICE.txt`.

> You must preserve these notices and licenses if redistributing this project or using it in a commercial product.


## Disclaimer
This software is provided "as-is" and intended for internal use only. External distribution or commercial deployment requires verification of all third-party licensing terms.

## Author

Developed by Jacob Ma
Machine Learning Intern @ IHI, Summer 2025
Contact: jacobdma218@gmail.com