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

Every query goes through a five-stage pipeline:

```
User Query
    │
    ▼
[1] Intent Classification (5-class multi-label)
    Multinomial Naive Bayes classifier detects student intent:
    • answer    → direct factual response (e.g., "What is backprop?")
    • explain   → detailed explanation with examples & reasoning
    • summarise → structured overview of a topic from notes
    • compare   → side-by-side comparison of concepts
    • quiz      → generate practice MCQ question to test understanding
    │
    ▼
[2] Retrieval
    TF-IDF (Path A) or Sentence Transformers + ChromaDB (Path B)
    fetches the top-3 most relevant chunks from uploaded PDFs.
    Supports filtering by a specific document.
    │
    ▼
[3] Confidence Gate (not_found detection)
    Replaces old classifier-based out-of-scope check.
    If top retrieved chunk's score < RETRIEVAL_CONFIDENCE_THRESHOLD,
    return "not found in notes" without calling LLM.
    This is document-aware — the retriever has already evaluated relevance.
    │
    ▼
[4] Intent-Specific Response Generation
    Based on predicted intent, send chunks + intent-tuned prompt to Gemini.
    • quiz:     Returns structured MCQ { question, options A-D, answer, explanation }
    • explain:  Longer, multi-step explanation with examples
    • summarise: Organized overview with headings or bullet points
    • compare:  Highlights similarities and differences
    • answer:   Concise 2-4 sentence direct response
    │
    ▼
[5] Response
    {
      intent:    { label, confidence },
      answer:    "..." or null (null if quiz),
      quiz:      { question, options, correct_answer, explanation } or null,
      sources:   [ { text, score, document_name } × 3 ],
      not_found: true/false (confidence gate result)
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
| Intent Classifier | Multinomial Naive Bayes (5-class) | 95 labelled examples across 5 intent types |
| Answer Generation | Google Gemini 2.5 Flash Lite | Free tier, intent-aware prompts, reliable grounding |
| Quiz Generation | Gemini 2.5 Flash Lite + JSON parsing | Structured MCQ with 4 options per question |
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
RETRIEVAL_MODE=semantic
SESSION_TTL_HOURS=24
MAX_FILE_SIZE_MB=20
CHUNK_SIZE_WORDS=300
CHUNK_OVERLAP_WORDS=50
TOP_K_CHUNKS=3
RETRIEVAL_CONFIDENCE_THRESHOLD=0.25
```

**Key Configuration Parameters:**

| Parameter | Default | Range | Description |
|---|---|---|---|
| `RETRIEVAL_MODE` | `semantic` | `tfidf` \| `semantic` | Retrieval backend |
| `SESSION_TTL_HOURS` | `24` | 1–168 | Session expiry in hours |
| `RETRIEVAL_CONFIDENCE_THRESHOLD` | `0.25` | 0.0–1.0 | Min similarity score for relevance. Use **0.25** for semantic mode, **0.10** for TF-IDF mode. If top chunk scores below this, return `not_found=True` |
| `TOP_K_CHUNKS` | `3` | 1–10 | Number of context chunks sent to LLM |

### 4. Train the intent classifier

This must be done **once** before the query endpoint will work:

```bash
# From backend/ with venv active
python training/train_classifier.py
```

Expected output:
```
Dataset loaded: 95 examples
Class distribution:
answer       30
summarise    20
explain      15
compare      15
quiz         15

Train: 76 | Test: 19

5-FOLD CROSS-VALIDATION
MultinomialNB        | CV F1 (weighted): 0.XX (±0.XX)
LogisticRegression   | CV F1 (weighted): 0.XX (±0.XX)

Winner: MultinomialNB (F1=0.XX)
Model saved → backend/models/intent_classifier.pkl

Generating evaluation artefacts...
✓ Confusion matrix saved
✓ Classification report saved
✓ Model comparison saved
```

This produces three files:
- `models/intent_classifier.pkl` — the trained 5-class model
- `evaluation/results/confusion_matrix.png` — 5×5 heatmap of classification errors
- `evaluation/results/classification_report.txt` — per-class metrics (precision, recall, F1)

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

The classifier is trained on `backend/training/intent_dataset.csv` — a manually curated set of ~95 labelled query examples across five intent classes.

### Intent Class Labels

| Label | Meaning | Example Query | Desired Output |
|---|---|---|---|
| `answer` | Student wants a specific factual response | *"What is backpropagation?"* | Concise 2-4 sentence answer |
| `explain` | Student wants detailed explanation with reasoning | *"Explain how backprop works in detail"* | Step-by-step explanation + examples |
| `summarise` | Student wants a topic overview | *"Summarize the chapter on neural networks"* | Structured overview with headings |
| `compare` | Student wants side-by-side comparison | *"Compare L1 and L2 regularization"* | Highlights similarities & differences |
| `quiz` | Student wants to test their understanding | *"Quiz me on gradient descent"* | MCQ with 4 options + explanation |

### Dataset Distribution

```
answer      30 examples (31%)
summarise   20 examples (21%)
explain     15 examples (16%)
compare     15 examples (16%)
quiz        15 examples (16%)
────────────────────────────
Total:      95 examples
```

### Extending the dataset

To improve classifier accuracy, add more examples to `intent_dataset.csv` in the format:

```csv
query,intent
What is the softmax function?,answer
Explain attention mechanisms step-by-step,explain
Compare ReLU vs sigmoid,compare
Summarize the transformer architecture,summarise
Quiz me on loss functions,quiz
```

Then re-run the training script:

```bash
python training/train_classifier.py
```

The script will automatically retrain, evaluate, and overwrite `models/intent_classifier.pkl`.

### Evaluation Output

After training, check the results folder:

```
evaluation/results/
├── confusion_matrix.png        ← Visual heatmap of classification errors
├── classification_report.txt   ← Precision, recall, F1 per class (5×5 matrix)
└── model_comparison.csv        ← Naive Bayes vs Logistic Regression scores
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

### Query response (regular intent: answer, explain, summarise, compare)

```json
{
  "success": true,
  "data": {
    "intent": {
      "label":      "answer",
      "confidence": 0.94
    },
    "answer": "Backpropagation is an algorithm that computes gradients...",
    "quiz": null,
    "sources": [
      {
        "chunk_id":      "sess_abc_doc_xyz_007",
        "document_name": "lecture_3.pdf",
        "text":          "Backpropagation works by computing...",
        "score":         0.87,
        "chunk_index":   7
      }
    ],
    "query_document_scope": "all",
    "not_found": false
  }
}
```

### Query response (quiz intent)

```json
{
  "success": true,
  "data": {
    "intent": {
      "label":      "quiz",
      "confidence": 0.89
    },
    "answer": null,
    "quiz": {
      "question":        "How does gradient descent minimize loss in neural networks?",
      "options": {
        "A": "By randomly adjusting all weights",
        "B": "By iteratively updating weights in the direction of negative gradients",
        "C": "By keeping weights fixed and only adjusting biases",
        "D": "By using pre-computed optimal weights"
      },
      "correct_answer": "B",
      "explanation": "Gradient descent uses the chain rule to compute gradients (backpropagation) and updates weights by moving in the direction opposite to the gradient to minimize loss."
    },
    "sources": [...],
    "query_document_scope": "all",
    "not_found": false
  }
}
```

### Query response (not found in notes)

When the top retrieved chunk's similarity score falls below `RETRIEVAL_CONFIDENCE_THRESHOLD`:

```json
{
  "success": true,
  "data": {
    "intent": {
      "label":      "answer",
      "confidence": 0.82
    },
    "answer": null,
    "quiz": null,
    "sources": [],
    "query_document_scope": "all",
    "not_found": true
  }
}
```

The frontend should display: *"I couldn't find this topic in your uploaded notes. Try rephrasing your question or uploading more relevant material."*

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

## Confidence Gate: Not Found Detection

**Key Architectural Change:** Out-of-scope detection has moved from the **classifier** to the **retriever**.

### Why This Matters

The original 3-class classifier treated out-of-scope as a hard class decision. This approach has two problems:

1. **Classifier doesn't see the actual documents** — it bases out-of-scope purely on word patterns
2. **Binary choice** — either fully out-of-scope or proceed, with no nuance

### New Approach: Retrieval-Based Gating

Instead:

1. **Classifier predicts one of 5 intents** (answer, explain, summarise, compare, quiz) — no out-of-scope class
2. **Retriever runs regardless** and evaluates the actual relevance against uploaded material
3. **Confidence gate checks**: If top chunk score < `RETRIEVAL_CONFIDENCE_THRESHOLD`, return `not_found: True`
4. **LLM is NOT called** if the gate fires — saves API quota and prevents hallucinations

### Example Workflow

```
Query: "Who invented the transistor?"
     ↓
Intent Classifier: predicts "answer" (confidence 0.87)
     ↓
Retriever: searches for relevant chunks in uploaded physics lecture PDFs
     ↓
Top chunk score: 0.08 (very low — transistor is barely mentioned in context)
     ↓
Confidence gate checks: 0.08 < RETRIEVAL_CONFIDENCE_THRESHOLD (0.25) ✗
     ↓
Response: { not_found: True, answer: null, sources: [] }
     ↓
Frontend displays: "I couldn't find this in your notes."
```

vs.

```
Query: "How does a transistor amplify current?"
     ↓
Intent Classifier: predicts "explain" (confidence 0.91)
     ↓
Retriever: searches for relevant chunks in physics lecture PDFs
     ↓
Top chunk score: 0.78 (strong match — detailed transistor section)
     ↓
Confidence gate checks: 0.78 > RETRIEVAL_CONFIDENCE_THRESHOLD (0.25) ✓
     ↓
LLM called with intent="explain" and retrieved chunks
     ↓
Response: { not_found: False, answer: "Detailed explanation...", sources: [...] }
```

### Tuning the Threshold

Edit `.env`:

```bash
RETRIEVAL_CONFIDENCE_THRESHOLD=0.25    # Semantic mode (all-MiniLM-L6-v2)
RETRIEVAL_CONFIDENCE_THRESHOLD=0.10    # TF-IDF mode
```

- **Higher threshold** → fewer false positives (system is stricter, may miss relevant content)
- **Lower threshold** → more answers attempted (system is lenient, may give wrong info)

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

1. **95 training examples is a moderate dataset.**
   The intent classifier may misclassify unusual phrasings or ambiguous queries. The 5-class setup (answer, explain, summarise, compare, quiz) is more fine-grained than the original 3-class, so edge cases are more likely. Adding domain-specific examples and retraining improves accuracy.

2. **Confidence gate tuning is retrieval-mode dependent.**
   The optimal `RETRIEVAL_CONFIDENCE_THRESHOLD` depends on your retrieval mode:
   - **Semantic**: typical range 0.20–0.35 (embeddings are dense, high scores mean strong semantic match)
   - **TF-IDF**: typical range 0.05–0.15 (sparse vectors are sparser, lower scores are still meaningful)
   Choosing the wrong threshold leads to either false positives ("here's an answer" when irrelevant) or false negatives ("not found" when content exists).

3. **TF-IDF is lexical, not semantic.**
   "automobile" and "car" are unrelated to TF-IDF. Queries using synonyms or paraphrasing will retrieve poor chunks. Switching to Path B (semantic) resolves this.

4. **Scanned PDFs are not supported.**
   pdfplumber reads the text layer only. Image-only PDFs (photographs of pages) return zero text and are rejected with a clear error. OCR support would require `pytesseract` — out of scope.

5. **Single-user, local deployment only.**
   The session model and filesystem persistence are not designed for concurrent users. For multi-user deployment, replace pickle with a vector database (Chroma Cloud, Pinecone) and sessions with a proper database.

6. **Gemini Flash context window.**
   Very long PDFs produce many chunks. Only the top-3 are sent to Gemini. If the relevant content is not in the top-3, the answer will be incomplete — this is a retrieval quality problem, not an LLM problem.

7. **Quiz generation quality depends on retrieved context.**
   If the retriever returns poor chunks, the quiz question may be shallow or misleading. The LLM strictly uses only the provided context, so quiz quality = retrieval quality.

---

## Course Context

**Course:** Artificial Intelligence (CSC-350) — Spring 2026
**University:** Sukkur IBA University, Department of Computer Science
**Instructor:** Dr. Muhammad Ismail Mangrio

### Course topics implemented

| Weeks | Topic | Implementation |
|---|---|---|
| Wk 3–4 | Problem Solving & Informed Search | Document retrieval modelled as a search problem. TF-IDF cosine similarity acts as the heuristic h(n) ranking candidate chunks — mirroring the A\* evaluation function. |
| Wk 11 | Uncertainty & Bayes' Rule | Multinomial Naive Bayes classifier assigns posterior probability P(intent \| query words) to each of 5 intent classes. |
| Wk 12–14 | ML Fundamentals — Classification & Evaluation | Full 5-class evaluation pipeline: train/test split (80/20), confusion matrix (5×5), weighted precision, recall, F1, 5-fold cross-validation. |
| Wk 12–14 | Supervised Learning — Logistic Regression | Trained alongside Naive Bayes as comparison baseline. Better-performing model selected for deployment. |
| Wk 15–16 | Confidence & Uncertainty Quantification | Confidence gate: retrieval-based out-of-scope detection using similarity threshold instead of classifier-based approach. Demonstrates that domain knowledge (retrieved content) trumps generic classifiers. |

### Extended Intent Classes

The original 3-class system (answer, summarise, out-of-scope) was expanded to **5 pragmatic intents** that capture how students actually interact with study materials:

```
answer    → Direct factual lookup     [30 examples → 31%]
summarise → Topic overview request   [20 examples → 21%]
explain   → Conceptual deep-dive     [15 examples → 16%]
compare   → Comparative analysis     [15 examples → 16%]
quiz      → Self-assessment / testing [15 examples → 16%]
```

Each intent triggers **intent-specific prompting** at the LLM stage:
- `answer`: Short, direct (2-4 sentences)
- `explain`: Long-form with step-by-step reasoning + examples
- `summarise`: Structured with headings/bullets
- `compare`: Explicit similarities & differences highlighted
- `quiz`: Generates MCQ with 4 options + explanation

---

## Intent-Specific Response Generation

Once the classifier predicts an intent and the retriever confirms relevance (passes confidence gate), the system generates a response **tailored to the predicted intent**. Each intent has its own prompt template:

### `answer` — Direct Factual Response

**Prompt Template:**
```
[Retrieved context blocks]

Answer the following question concisely and directly (2-4 sentences maximum):
{user_query}
```

**Example Response:**
> "Backpropagation is an algorithm that computes gradients of the loss with respect to weights using the chain rule. These gradients are then used by an optimizer to update weights iteratively, gradually reducing loss."

---

### `explain` — Detailed Explanation with Examples

**Prompt Template:**
```
[Retrieved context blocks]

Provide a detailed explanation for the following, including examples and 
step-by-step reasoning where relevant. Base your explanation entirely on the 
context above:
{user_query}
```

**Example Response:**
> "Backpropagation works through these steps: (1) Forward pass — data flows through layers, computing activations. (2) Loss computation — measure the error. (3) Backward pass — compute gradients using the chain rule from output to input. (4) Weight update — move weights in the negative gradient direction. For example, in a 2-layer network, the gradient with respect to the first layer's weights is computed by multiplying the output layer's gradient with the input layer's activations, demonstrating the chain rule..."

---

### `summarise` — Structured Topic Overview

**Prompt Template:**
```
[Retrieved context blocks]

Provide a structured, comprehensive summary of the following based on the 
context above. Cover all key points. Use clear headings or bullet points:
{user_query}
```

**Example Response:**
```
## Key Points on Backpropagation

### Definition
Backpropagation is an algorithm for training neural networks by computing 
gradients of the loss with respect to network parameters.

### Core Components
- Forward pass: propagate activations through layers
- Loss computation: measure error against true labels
- Backward pass: compute gradients using chain rule
- Optimization: update weights iteratively

### Benefits
- Efficient gradient computation via chain rule
- Applicable to any differentiable network architecture
- Foundation of modern deep learning training
```

---

### `compare` — Comparative Analysis

**Prompt Template:**
```
[Retrieved context blocks]

Based strictly on the context above, compare and contrast the concepts in the 
following question. Present similarities and differences clearly:
{user_query}
```

**Example Response:**
> "**Similarities:** Both L1 and L2 regularization penalize large weights to prevent overfitting. Both are added to the loss function during training.
> 
> **Differences:** L1 (Lasso) adds the absolute value of weights; L2 (Ridge) adds the squared weights. L1 can drive weights exactly to zero (feature selection); L2 shrinks but rarely zeros out. L1 produces sparse models; L2 produces dense models."

---

### `quiz` — Practice MCQ Generation

**Prompt Template:**
```
[Retrieved context blocks]

Generate a multiple-choice question based on the context above to test 
understanding of: {user_query}

Respond with valid JSON: {"question": "...", "options": {"A": "...", ...}, 
"correct_answer": "A/B/C/D", "explanation": "..."}
```

**Example Response:**
```json
{
  "question": "What is the primary advantage of gradient descent?",
  "options": {
    "A": "It guarantees finding the global minimum",
    "B": "It efficiently computes gradients and updates weights iteratively",
    "C": "It is faster than manual weight adjustment",
    "D": "It only works for linear models"
  },
  "correct_answer": "B",
  "explanation": "GD efficiently uses the chain rule to compute gradients in O(n) time and iteratively moves toward a minimum. It finds local minima, not guaranteed global (rules out A). C and D misrepresent GD's mechanics."
}
```

The frontend receives this as a structured quiz card for interactive practice.

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