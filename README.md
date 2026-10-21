# AI Study Assistant

> Ask questions about your lecture PDFs and get responses grounded in retrieved passages from your notes.

An independently built, full-stack study assistant. It combines PDF parsing, intent classification, two interchangeable retrieval approaches, and Gemini response generation in a local web application. Responses include retrieved sources, and a retrieval-confidence gate can abstain when the notes do not appear relevant.

## Features

- Upload and manage PDF documents within local, time-limited study sessions.
- Ask questions in natural language and filter retrieval to a selected document.
- Classify requests as `answer`, `explain`, `summarise`, `compare`, or `quiz`.
- Search with either TF-IDF or semantic embeddings and ChromaDB.
- Show source passages and similarity scores with generated responses.
- Abstain from calling the LLM when the top retrieval score is below a configurable threshold.
- Generate multiple-choice quizzes grounded in retrieved note passages.

## How it works

1. Extract text from an uploaded PDF and split it into overlapping chunks.
2. Index chunks using the selected retrieval backend: TF-IDF or sentence-transformer embeddings in ChromaDB.
3. Classify the user's request and retrieve the top matching chunks.
4. Apply the confidence threshold. If the best score is too low, return a not-found response without calling Gemini.
5. Otherwise, send the query and retrieved context to Gemini using an intent-specific prompt, then return the response and source passages.

This grounding design is intended to keep responses tied to the uploaded notes; it does not guarantee that every generated answer is correct.

## Stack

| Area | Technologies |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS, Axios |
| Backend | Python, FastAPI, Pydantic |
| PDF processing | pdfplumber |
| Lexical retrieval | scikit-learn TF-IDF and cosine similarity |
| Semantic retrieval | sentence-transformers (`all-MiniLM-L6-v2`) and ChromaDB |
| Intent classification | scikit-learn; compares Multinomial Naive Bayes and Logistic Regression |
| Response generation | Google Gemini 2.5 Flash Lite |
| Local persistence | Session files, TF-IDF pickle artifacts, and ChromaDB |

## Architecture

```text
React + Vite frontend
        │ HTTP / JSON
        ▼
FastAPI API
  ├─ Session and document routes
  ├─ PDF parsing and chunking
  ├─ Intent classifier
  ├─ TF-IDF or semantic retrieval
  └─ Confidence gate and Gemini response generation
        │
        ▼
Local session files and retrieval indexes
```

```text
backend/
  app.py
  config.py
  modules/       # PDF processing, sessions, classifiers, retrievers, Gemini
  routers/       # Session, upload, document, and query endpoints
  schemas/
  training/
  evaluation/
  tests/
frontend/
  src/
    api/
    components/
    hooks/
```

## Requirements

- Python 3.11
- Node.js and npm versions supported by the Vite version in `frontend/package.json`
- A Google Gemini API key

## Setup and run

### 1. Clone the project

```bash
git clone https://github.com/sajidghoto/study-assistant.git
cd study-assistant
```

### 2. Configure and install the backend

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set your own `GEMINI_API_KEY`. The example file contains a placeholder only. Its retrieval settings match the current backend defaults; evaluate the confidence threshold for your data and selected retriever rather than treating it as a universal relevance score.

The repository includes a trained intent-classifier artifact. To retrain it and regenerate classifier evaluation outputs, run from `backend/`:

```powershell
python training/train_classifier.py
```

### 3. Install and run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

### 4. Start the backend

In another terminal, from `backend/` with the virtual environment activated:

```powershell
uvicorn app:app --reload --port 8000
```

Open the frontend at `http://localhost:5173`. Interactive API documentation is available at `http://localhost:8000/docs`; the health endpoint is `http://localhost:8000/api/v1/health`.

## Configuration

Backend settings are defined in `backend/config.py` and can be set through `backend/.env`.

| Variable | Current default | Purpose |
|---|---:|---|
| `GEMINI_API_KEY` | Required | API key for response generation |
| `RETRIEVAL_MODE` | `semantic` | Select `tfidf` or `semantic` |
| `RETRIEVAL_CONFIDENCE_THRESHOLD` | `0.05` | Minimum top similarity score before generation proceeds |
| `TOP_K_CHUNKS` | `3` | Maximum retrieved chunks passed to the response generator |
| `SESSION_TTL_HOURS` | `24` | Session lifetime |
| `MAX_FILE_SIZE_MB` | `20` | Maximum accepted PDF size |
| `CHUNK_SIZE_WORDS` | `300` | Target chunk length in words |
| `CHUNK_OVERLAP_WORDS` | `50` | Word overlap between neighboring chunks |

The semantic backend downloads its embedding model on first use. Re-upload and re-index documents after changing retrieval modes; indexes are backend-specific.

## API overview

All routes use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Backend health and active retrieval mode |
| `POST` | `/session` | Create a session |
| `GET` | `/session/{id}` | Read session state |
| `DELETE` | `/session/{id}` | Delete a session and its data |
| `POST` | `/session/{id}/upload` | Upload and index a PDF |
| `GET` | `/session/{id}/documents` | List session documents |
| `DELETE` | `/session/{id}/document/{doc_id}` | Remove a document |
| `POST` | `/session/{id}/query` | Ask a question about uploaded notes |

Use `/docs` for request schemas and interactive endpoint details. A query can optionally include a `document_id` to restrict retrieval to one PDF.

## Evaluation

### Intent classifier

`backend/training/train_classifier.py` compares Multinomial Naive Bayes and Logistic Regression, runs cross-validation on the training split, evaluates a held-out split, and saves the selected model and reports. The current report is an initial baseline from a small dataset and held-out set; it should not be presented as evidence of broad generalization.

### Retrieval

`backend/evaluation/precision_at_3.py` retrieves the top three chunks for each question in `backend/evaluation/test_queries.csv` and exports them for manual relevance annotation. Its computation mode rejects missing or incomplete annotations and retrieval errors.

The question set and annotation process are still being developed. There is not yet a completed, fully annotated retrieval benchmark, so no Precision@3 result is claimed here.

## Tests and checks

Backend tests:

```powershell
cd backend
pytest tests/ -v
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Limitations

- Retrieval quality and confidence thresholds still need evaluation against a verified, annotated benchmark.
- PDF extraction relies on a text layer; scanned image-only PDFs are not supported.
- The application is designed for local, single-user use, not concurrent multi-user deployment.
- Generated answers and quizzes can still be incorrect; review the returned sources.
- Semantic search requires a local embedding-model download. TF-IDF is lexical and may miss paraphrases or synonyms.
