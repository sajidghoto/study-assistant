# Intent-Aware Agentic Study Assistant

> Upload your lecture notes. Ask questions. Get answers grounded strictly in your own material.

A full-stack AI study tool built for university students. Upload PDF lecture notes, ask natural-language questions, and receive answers that are always grounded in your uploaded content — never hallucinated. Every response shows you **what the system understood you were asking** (intent), **what it found** (source chunks with similarity scores), and **what it generated** (a grounded answer).

---

## Table of Contents

- [What This System Does](#what-this-system-does)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Training the Intent Classifier](#training-the-intent-classifier)
- [API Reference](#api-reference)
- [Retrieval Modes](#retrieval-modes)
- [Evaluation](#evaluation)
- [Known Limitations](#known-limitations)
- [Course Context](#course-context)
- [Team](#team)

---

## What This System Does

Every query goes through a four-stage pipeline:

```
User Query
    │
    ▼
[1] Intent Classification
    Naive Bayes classifier detects whether the user wants:
    • answer       → direct factual response
    • summarise    → topic overview from notes
    • out-of-scope → question has nothing to do with uploaded material

    If out-of-scope → skip everything below, return instantly.
    │
    ▼
[2] Retrieval
    TF-IDF (Path A) or Sentence Transformers + ChromaDB (Path B)
    fetches the top-3 most relevant chunks from uploaded PDFs.
    Supports filtering by a specific document.
    │
    ▼
[3] Answer Generation
    Retrieved chunks are sent to Gemini 1.5 Flash with a strict
    grounding prompt. The model answers ONLY from the provided context.
    If the answer is not there, it says so explicitly.
    │
    ▼
[4] Response
    {
      intent:  { label, confidence },
      answer:  "...",
      sources: [ { text, score, document_name } × 3 ]
    }
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│           React Frontend  :5173             │
│  FileUpload │ ChatWindow │ SourcesPanel     │
└────────────────────┬────────────────────────┘
                     │ HTTP / JSON
┌────────────────────▼────────────────────────┐
│          FastAPI Backend  :8000             │
│                                             │
│  routers/         modules/                 │
│  ├─ session.py    ├─ pdf_parser.py         │
│  ├─ upload.py     ├─ session_manager.py    │
│  ├─ documents.py  ├─ retriever_tfidf.py    │
│  └─ query.py      ├─ retriever_semantic.py │
│                   ├─ classifier.py         │
│                   └─ llm_bridge.py         │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│              Local Filesystem               │
│  data/sessions/<id>/                        │
│  ├─ metadata.json   (session registry)      │
│  ├─ tfidf_matrix.pkl                        │
│  ├─ vectorizer.pkl                          │
│  └─ chunks.pkl                              │
│  data/chromadb/<id>/  (Path B only)         │
│  models/intent_classifier.pkl               │
└─────────────────────────────────────────────┘
```

Sessions expire after **24 hours**. Expiry is enforced lazily on every load — no background jobs required.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | React.js + Vite + Tailwind CSS | Fast dev server, component model, utility CSS |
| HTTP Client | Axios | Better error handling than native fetch |
| Backend | Python + FastAPI | Auto-docs (Swagger), Pydantic validation, async support |
| PDF Parsing | pdfplumber | Handles multi-column layouts better than PyPDF2 |
| Retrieval (Path A) | scikit-learn TF-IDF + cosine similarity | Lexical, fast, no GPU, course-aligned |
| Retrieval (Path B) | sentence-transformers + ChromaDB | Semantic meaning, local, no API cost |
| Intent Classifier | Multinomial Naive Bayes (primary) + Logistic Regression (comparison) | Sample-efficient on 60 examples |
| LLM | Google Gemini 1.5 Flash | Free tier, sufficient for grounded Q&A |
| Persistence | pickle (Path A) / ChromaDB files (Path B) | No database needed for local single-user app |

---

## Project Structure

```
study-assistant/
│
├── backend/
│   ├── .env                        ← API keys (never committed)
│   ├── .env.example                ← Template — copy to .env
│   ├── app.py                      ← FastAPI entry point
│   ├── config.py                   ← All settings (reads .env)
│   ├── requirements.txt
│   │
│   ├── modules/                    ← Business logic
│   │   ├── pdf_parser.py           ← Extract + chunk PDFs
│   │   ├── session_manager.py      ← Session CRUD + TTL
│   │   ├── retriever_tfidf.py      ← Path A retrieval
│   │   ├── retriever_semantic.py   ← Path B retrieval
│   │   ├── classifier.py           ← Intent prediction
│   │   └── llm_bridge.py           ← Gemini API call
│   │
│   ├── routers/                    ← FastAPI route handlers
│   │   ├── session.py
│   │   ├── upload.py
│   │   ├── documents.py
│   │   └── query.py
│   │
│   ├── schemas/                    ← Pydantic models
│   │   ├── session.py
│   │   ├── document.py
│   │   └── query.py
│   │
│   ├── training/
│   │   ├── intent_dataset.csv      ← 60 labelled examples
│   │   └── train_classifier.py     ← Run once to train
│   │
│   ├── evaluation/
│   │   ├── precision_at_3.py
│   │   └── results/                ← Generated evaluation outputs
│   │
│   ├── models/
│   │   └── intent_classifier.pkl   ← Trained model (committed)
│   │
│   ├── data/
│   │   ├── sessions/               ← TF-IDF pickle files (not committed)
│   │   └── chromadb/               ← ChromaDB vector files (not committed)
│   │
│   └── tests/
│       ├── conftest.py
│       └── test_*.py
│
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api/                    ← Axios API calls
│       ├── components/             ← React components
│       ├── hooks/                  ← Custom hooks
│       └── utils/                  ← Constants + formatters
│
├── .gitignore
└── README.md
```

---

## Prerequisites

Make sure these are installed before continuing:

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

You also need a **Google Gemini API key** (free tier):
1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key — you will paste it into `.env` below

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/study-assistant.git
cd study-assistant
```

### 2. Backend setup

```bash
cd backend

# Create and activate virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Install all dependencies (~3-5 minutes on first run)
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
# Copy the template
copy .env.example .env
```

Open `.env` and fill in your values:

```bash
GEMINI_API_KEY=your_actual_gemini_api_key_here
RETRIEVAL_MODE=tfidf
SESSION_TTL_HOURS=24
MAX_FILE_SIZE_MB=20
CHUNK_SIZE_WORDS=300
CHUNK_OVERLAP_WORDS=50
TOP_K_CHUNKS=3
```

> **Never commit `.env` to git.** It is already listed in `.gitignore`.

### 4. Train the intent classifier

This must be done **once** before the query endpoint will work:

```bash
# From backend/ with venv active
python training/train_classifier.py
```

Expected output:
```
Dataset loaded: 60 examples
Class distribution:
answer          20
out-of-scope    20
summarise       20

Train: 48 | Test: 12

5-FOLD CROSS-VALIDATION
MultinomialNB        | CV F1: 0.XXX (±0.XXX)
LogisticRegression   | CV F1: 0.XXX (±0.XXX)

Winner: MultinomialNB (F1=0.XXX)
Model saved → backend/models/intent_classifier.pkl
```

This produces three files:
- `models/intent_classifier.pkl` — the trained model
- `evaluation/results/confusion_matrix.png` — visual evaluation
- `evaluation/results/classification_report.txt` — per-class metrics

### 5. Frontend setup

```bash
cd ../frontend
npm install
```

---

## Running the Application

You need **two terminals** running simultaneously.

**Terminal 1 — Backend:**
```bash
cd backend
venv\Scripts\activate
uvicorn app:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open your browser:

| URL | Purpose |
|---|---|
| `http://localhost:5173` | The application UI |
| `http://localhost:8000/docs` | Swagger API docs (interactive) |
| `http://localhost:8000/redoc` | ReDoc API docs (readable) |
| `http://localhost:8000/api/v1/health` | Backend health check |

---

## Training the Intent Classifier

The classifier is trained on `backend/training/intent_dataset.csv` — a manually curated set of 60 labelled query examples across three classes.

### Class labels

| Label | Meaning | Example query |
|---|---|---|
| `answer` | Student wants a specific factual response | *"What is backpropagation?"* |
| `summarise` | Student wants a topic overview | *"Summarize the chapter on neural networks"* |
| `out-of-scope` | Query has nothing to do with the notes | *"Who won the cricket World Cup?"* |

### Extending the dataset

To improve classifier accuracy, add more examples to `intent_dataset.csv` and re-run the training script:

```bash
python training/train_classifier.py
```

The script will automatically retrain, evaluate, and overwrite `models/intent_classifier.pkl`.

### Evaluation output

After training, check the results folder:

```
evaluation/results/
├── confusion_matrix.png        ← visual heatmap of classification errors
├── classification_report.txt   ← precision, recall, F1 per class
└── model_comparison.csv        ← Naive Bayes vs Logistic Regression
```

---

## API Reference

All endpoints are prefixed with `/api/v1`. The full interactive reference is at `http://localhost:8000/docs`.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Backend health + active retrieval mode |
| `POST` | `/session` | Create a new session |
| `GET` | `/session/{id}` | Get session state (documents, chunk count) |
| `DELETE` | `/session/{id}` | Delete session and all its data |
| `POST` | `/session/{id}/upload` | Upload a PDF and index it |
| `GET` | `/session/{id}/documents` | List all uploaded documents |
| `DELETE` | `/session/{id}/document/{doc_id}` | Remove a document from session |
| `POST` | `/session/{id}/query` | Ask a question |

### Query request body

```json
{
  "query": "What is backpropagation?",
  "document_id": null
}
```

Set `document_id` to a specific document ID to restrict retrieval to that PDF only. Set to `null` to search across all uploaded documents.

### Query response

```json
{
  "success": true,
  "data": {
    "intent": {
      "label":      "answer",
      "confidence": 0.94
    },
    "answer": "Backpropagation is an algorithm...",
    "sources": [
      {
        "chunk_id":      "sess_abc_doc_xyz_007",
        "document_name": "lecture_3.pdf",
        "text":          "Backpropagation works by...",
        "score":         0.87,
        "chunk_index":   7
      }
    ],
    "query_document_scope": "all"
  }
}
```

### Error response format

```json
{
  "success": false,
  "error": {
    "code":    "SESSION_EXPIRED",
    "message": "Your session has expired. Please start a new session.",
    "detail":  "expires_at was 2026-03-27T10:00:00Z"
  }
}
```

---

## Retrieval Modes

The system supports two retrieval backends switchable via `.env`:

### Path A — TF-IDF (default, `RETRIEVAL_MODE=tfidf`)

```
How it works:
  Chunks and queries are represented as sparse vectors over a shared
  vocabulary. Similarity is cosine distance between these vectors.

Strength:  Fast, fully local, no model download, deterministic.
Weakness:  Lexical only. "async" and "asynchronous" are unrelated.
           Poor results on paraphrased or synonym-heavy queries.

Best for:  Course projects, exact-term queries, offline environments.
```

### Path B — Semantic (`RETRIEVAL_MODE=semantic`)

```
How it works:
  Chunks and queries are encoded into 384-dimensional dense vectors
  using all-MiniLM-L6-v2 (sentence-transformers). ChromaDB stores
  these vectors locally and retrieves by cosine similarity.

Strength:  Understands meaning. "async" matches "asynchronous".
           Handles synonyms, paraphrasing, and natural language well.
Weakness:  ~90MB model download on first use. Slightly slower.

Best for:  Production-quality retrieval, natural language queries.
```

To switch modes, edit `.env` and restart the backend:
```bash
RETRIEVAL_MODE=semantic   # or tfidf
```

> **Note:** Switching modes on an existing session will not re-index already uploaded documents. Delete the session and re-upload your PDFs after switching.

---

## Evaluation

### Intent Classifier

Run the training script to generate all classifier evaluation outputs automatically. Key metrics to report:

- Weighted F1 score (target: ≥ 0.80)
- Per-class precision, recall, F1
- Confusion matrix
- Naive Bayes vs Logistic Regression comparison

### Retrieval — Precision@3

```bash
cd backend
python evaluation/precision_at_3.py
```

This script loads 20 manually prepared test questions, retrieves top-3 chunks for each, and outputs a CSV for manual relevance marking. Final score = average proportion of relevant chunks across 20 queries.

Results are saved to `evaluation/results/precision_at_3_results.csv`.

---

## Known Limitations

These are documented transparently and discussed in the project report:

1. **TF-IDF is lexical, not semantic.**
   "automobile" and "car" are unrelated to TF-IDF. Queries using synonyms or paraphrasing will retrieve poor chunks. Switching to Path B (semantic) resolves this.

2. **Scanned PDFs are not supported.**
   pdfplumber reads the text layer only. Image-only PDFs (photographs of pages) return zero text and are rejected with a clear error. OCR support would require `pytesseract` — out of scope.

3. **60 training examples is a small dataset.**
   The intent classifier may misclassify unusual phrasings. Adding more labelled examples and retraining improves accuracy.

4. **Single-user, local deployment only.**
   The session model and filesystem persistence are not designed for concurrent users. For multi-user deployment, replace pickle with a vector database (Chroma Cloud, Pinecone) and sessions with a proper database.

5. **Gemini Flash context window.**
   Very long PDFs produce many chunks. Only the top-3 are sent to Gemini. If the relevant content is not in the top-3, the answer will be incomplete — this is a retrieval quality problem, not an LLM problem.

---

## Course Context

**Course:** Artificial Intelligence (CSC-350) — Spring 2026
**University:** Sukkur IBA University, Department of Computer Science
**Instructor:** Dr. Muhammad Ismail Mangrio

### Course topics implemented

| Weeks | Topic | Implementation |
|---|---|---|
| Wk 3–4 | Problem Solving & Informed Search | Document retrieval modelled as a search problem. TF-IDF cosine similarity acts as the heuristic h(n) ranking candidate chunks — mirroring the A\* evaluation function. |
| Wk 11 | Uncertainty & Bayes' Rule | Multinomial Naive Bayes classifier assigns posterior probability to each intent class given query tokens. |
| Wk 12–14 | ML Fundamentals — Classification & Evaluation | Full evaluation pipeline: train/test split, confusion matrix, precision, recall, F1, cross-validation. |
| Wk 12–14 | Supervised Learning — Logistic Regression | Trained alongside Naive Bayes as comparison baseline. Better-performing model selected for deployment. |

---

## Team

| Member | Role | Primary Deliverable |
|---|---|---|
| Umar Daraz (053-23-0004) | Backend — Data Pipeline | PDF parsing, chunking, TF-IDF retriever, session management |
| Sajid Ali (023-23-0084) | Backend — AI/ML | Intent classifier, evaluation metrics, Gemini bridge, report |
| Member 3 | Frontend | React UI, Axios integration, all components |

---

## Running Tests

```bash
cd backend
venv\Scripts\activate
pytest tests/ -v
```

To run a specific test file:
```bash
pytest tests/test_pdf_parser.py -v
pytest tests/test_classifier.py -v
```

---

## Quick Start (TL;DR)

```bash
# 1. Clone and enter project
git clone https://github.com/your-username/study-assistant.git
cd study-assistant

# 2. Backend
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then add your GEMINI_API_KEY to .env
python training/train_classifier.py

# 3. Frontend (new terminal)
cd frontend
npm install

# 4. Run both servers
# Terminal 1:
cd backend && venv\Scripts\activate && uvicorn app:app --reload --port 8000
# Terminal 2:
cd frontend && npm run dev

# 5. Open browser
# App:  http://localhost:5173
# Docs: http://localhost:8000/docs
```