# Document Intelligence Asynchronous Pipeline

An enterprise-grade, fault-tolerant, asynchronous document processing pipeline implementing the **Claim-Check Pattern**, built with **FastAPI**, **Celery**, **Redis**, **PostgreSQL 16**, **Tesseract OCR**, and a modern interactive web dashboard — fully containerized and runnable with a single **Docker Compose** command.

---

## 🌟 Architectural Overview & Claim-Check Pattern

Processing documents synchronously is unreliable due to variable file sizes, complex OCR operations, and network timeouts. This pipeline solves this challenge by decoupling document ingestion from execution using the **Claim-Check Pattern**:

```
                    +------------------------------------------+
                    |           Client / Web Interface         |
                    +--------------------+---------------------+
                                         |
                       1. POST /upload   | 6. Poll GET /jobs/{id}
                                         v
                    +--------------------+---------------------+
                    |           FastAPI Ingestion Service       |
                    +---------+----------------------+---------+
                              |                      |
             2. Save binary   |                      | 3. Create Record (PENDING)
                              v                      v
              +---------------+---------------+  +---+--------------------+
              | Shared Volume Storage         |  | PostgreSQL Database    |
              | (/app/storage/uploads)        |  | (document_jobs table)  |
              +---------------+---------------+  +---+--------------------+
                              |                      ^
                              | 4. Push Job ID       | 7. Update Status & Text
                              v                      |
                    +---------+----------------------+---------+
                    |          Redis Message Broker            |
                    +--------------------+---------------------+
                                         |
                                         | 5. Consume Task
                                         v
                    +--------------------+---------------------+
                    | Celery Worker + Tesseract OCR Engine     |
                    +------------------------------------------+
```

### Key Highlights
1. **Claim-Check Pattern**: Incoming binary documents (PDF, PNG, JPG, TXT, DOCX) are validated and saved immediately to a shared storage volume. Only a lightweight claim-check ticket (`job_id`) is enqueued into Redis, eliminating Redis memory bloat and queue serialization overhead.
2. **Hybrid Document Intelligence Engine**: 
   - **Vectorial PDFs**: Direct high-speed text parsing via `PyMuPDF` (`fitz`).
   - **Scanned PDFs & Images**: Automatic fallback to high-resolution page rendering and `Tesseract OCR` (`spa+eng`).
   - **DOCX & TXT**: Native structural parsing with `python-docx` and multi-encoding readers.
3. **Resilience & Fault Tolerance**:
   - `task_acks_late = True` and `task_reject_on_worker_lost = True` ensure no job is lost if workers or containers are killed mid-processing.
   - Comprehensive error handling updates database records to `FAILED` with explicit error tracebacks so jobs never stay in non-terminal states.
4. **Monitoring & Dashboard**: Integrated **Celery Flower** monitoring on port `5555` and a dynamic glassmorphism web UI on port `8000`.

---

## 🛠️ Technology Stack

| Component | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **API Framework** | FastAPI / Uvicorn | `0.110+` | High-performance asynchronous REST API |
| **Task Queue** | Celery | `5.3+` | Asynchronous worker task execution & retries |
| **Message Broker** | Redis | `7.2-alpine` | Distributed message broker and result backend |
| **Database** | PostgreSQL | `16-alpine` | Relational storage for job tracking & metadata |
| **ORM & Migrations** | SQLAlchemy | `2.0+` | Database models and connection pooling |
| **OCR Engine** | Tesseract OCR | `5.0+` | Multilingual text recognition (Spanish + English) |
| **PDF Parser** | PyMuPDF (fitz) / pypdf | `1.23+` | C-backed high-speed PDF text extraction |
| **Docx Parser** | python-docx | `1.1+` | Microsoft Word paragraph & table extraction |
| **Monitoring** | Celery Flower | `2.0+` | Real-time queue metrics and worker dashboard |
| **Containerization** | Docker Compose | `v2 / v5` | Single-command orchestration of all 5 services |

---

## 🚀 Quick Start Guide

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + Docker Compose installed.

### Running the Complete System
Clone the repository and run the single Docker Compose command:

```bash
git clone https://github.com/RusselKu/Document-Intelligence-Async-Pipeline.git
cd Document-Intelligence-Async-Pipeline

# Start all 5 services in detached mode
docker compose up --build -d
```

### Accessing Services
- **Web Dashboard & UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Celery Flower Monitoring**: [http://localhost:5555](http://localhost:5555) *(Credentials: `admin` / `admin`)*
- **PostgreSQL Database**: `localhost:5432` (`user: postgres`, `pass: postgres`, `db: doc_intelligence`)

---

## 📡 REST API Reference

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload document for async processing (Claim-Check) | `202 Accepted` |
| `GET` | `/api/v1/jobs/{job_id}` | Poll job status, progress percentage, & duration | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/result` | Fetch extracted text & enriched metadata report | `200 OK / 409 Conflict` |
| `GET` | `/api/v1/jobs` | List recent job execution history (paginated) | `200 OK` |
| `GET` | `/api/v1/jobs/{job_id}/benchmark` | Run empirical parser benchmark (PyMuPDF vs Tesseract) | `200 OK` |
| `GET` | `/health` | Service healthcheck endpoint | `200 OK` |

---

## 🔬 Empirical Parser Benchmark (Part 3)

The pipeline incorporates a programmatic benchmarking engine (`app/services/benchmark.py`) to empirically evaluate text extraction strategies rather than relying on arbitrary library selection:

### Benchmark Metrics Example (`U1T02.pdf` - 2 Pages, 433 Words):

```json
{
  "test_file": "U1T02.pdf",
  "file_format": "pdf",
  "results": [
    {
      "parser_name": "PyMuPDF (fitz)",
      "extraction_time_sec": 0.087,
      "characters_extracted": 2929,
      "words_extracted": 430,
      "success": true,
      "notes": "C-backed vector parser. Recommended for native PDFs."
    },
    {
      "parser_name": "pypdf",
      "extraction_time_sec": 0.0294,
      "characters_extracted": 2927,
      "words_extracted": 430,
      "success": true,
      "notes": "Pure Python parser."
    },
    {
      "parser_name": "Tesseract OCR (spa+eng)",
      "extraction_time_sec": 1.7471,
      "characters_extracted": 2900,
      "words_extracted": 430,
      "success": true,
      "notes": "Full rasterization + OCR engine. Essential for scanned PDFs."
    }
  ],
  "recommended_parser": "PyMuPDF (fitz)"
}
```

---

## 🛡️ Edge Scenarios & Resilience Architecture

1. **Unsupported Formats**: Rejected immediately at the API boundary with `400 Bad Request` before persisting or enqueuing.
2. **Corrupted / Damaged Files**: Caught by try/except blocks inside Celery workers. The database job status is atomicaly set to `FAILED` with the full `error_message` traceback.
3. **Abrupt Worker Crash / Container Restart**:
   - `task_acks_late = True`: Celery keeps the task message in Redis until worker completion. If a worker dies mid-task, Redis re-delivers the task to another available worker.
   - Database entries track `started_at` timestamps to allow automated recovery of stale jobs upon service restart.

---

## 📂 Repository Structure

```
Document-Intelligence-Async-Pipeline/
├── docker-compose.yml       # 5-Service Docker Orchestration
├── Dockerfile.api           # FastAPI Image with Tesseract & System Dependencies
├── Dockerfile.worker        # Celery Worker Image with Tesseract & System Dependencies
├── requirements.txt         # Python Package Requirements
├── README.md                # Main Overview & Quick Start (This Document)
├── test_all_formats.py      # E2E Automated Verification Test Suite
├── docs/                    # Technical Deliverables & Architecture Report
│   ├── REPORT.md            # Detailed Architecture & Technical Decision Report
│   └── REPORT.pdf           # Compiled PDF Architecture Deliverable Report
├── storage/                 # Shared Persistent Volume
│   ├── uploads/             # Claim-Check Binary Upload Storage
│   └── extracted/           # Extracted Plain Text File Storage
└── app/
    ├── main.py              # FastAPI Application Lifespan & Entrypoint
    ├── config.py            # Pydantic v2 Environment Settings
    ├── api/v1/              # API Endpoints & Routers
    ├── core/                # Claim-Check Validation & Storage Logic
    ├── db/                  # SQLAlchemy Session & DocumentJob ORM Models
    ├── schemas/             # Pydantic Request/Response Schemas
    ├── services/            # Extractor Engine, Metadata Generator & Benchmarks
    ├── tasks/               # Celery App & Asynchronous Task Definitions
    └── static/              # Modern Web Dashboard UI (HTML, CSS, JS)
```

---

## 📄 License & Deliverables

This project fulfills all requirements specified in **U1T02: Document Intelligence Asynchronous Pipeline**. Technical architectural decisions and diagrams are available in `docs/REPORT.md` and `docs/REPORT.pdf`.
