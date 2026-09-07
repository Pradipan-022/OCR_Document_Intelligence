[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]()

# 📄 OCR Document Intelligence Platform

A decoupled web application for intelligent document processing, quality profiling, and structured data extraction. The platform features an automated quality assessment module, an adaptive OpenCV image enhancement pipeline, and multi-engine OCR orchestration across **PaddleOCR**, **Tesseract**, and **EasyOCR**.

---

## Table of Contents

- [Screenshots & Demo](#screenshots--demo)
- [Platform Workflows](#platform-workflows)
- [Technical Architecture & Core Features](#technical-architecture--core-features)
  - [1. Document Ingestion & Tenant Storage](#1-document-ingestion--tenant-storage)
  - [2. Quality Profiling & Preprocessing Pipelines](#2-quality-profiling--preprocessing-pipelines)
  - [3. Multi-Engine OCR & Extraction](#3-multi-engine-ocr--extraction)
  - [4. Validation, Review, & Database](#4-validation-review--database)
- [Tech Stack](#tech-stack)
- [Project Directory Structure](#project-directory-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [Core API Endpoints](#core-api-endpoints)
- [Contributing](#contributing)
- [License](#license)

---

## Screenshots & Demo

### Login Page

<p align="center">
  <img src="docs/media/login-page.png" alt="Login Page Screenshot" width="700"/>
</p>

<!-- Replace the src above with a screenshot of the login/auth page, e.g. docs/media/login-page.png -->

### Feature Walkthroughs

| Ingestion | Preprocessing |
|:---:|:---:|
| <img src="docs/media/ingestion-demo.gif" alt="Document Ingestion Demo" width="380"/> | <img src="docs/media/preprocessing-demo.gif" alt="Preprocessing Demo" width="380"/> |
| *Batch document upload and tenant-scoped storage* | *Quality assessment and enhancement pipeline selection* |

| History | OCR Results |
|:---:|:---:|
| <img src="docs/media/history-demo.gif" alt="Document History Demo" width="380"/> | <img src="docs/media/ocr-results-demo.gif" alt="OCR Results Demo" width="380"/> |
| *Historical change audit log and document tracking* | *Multi-engine extraction, scoring, and human-in-the-loop review* |

<!--
  GIF placeholders — add recordings to docs/media/ using these filenames, or update the paths above:
    - docs/media/ingestion-demo.gif
    - docs/media/preprocessing-demo.gif
    - docs/media/history-demo.gif
    - docs/media/ocr-results-demo.gif
-->

---

## Platform Workflows

The Streamlit frontend is organized around four core workflows:

1. **Ingestion** — Upload and stage documents for processing
2. **Preprocessing** — Assess quality and apply enhancement pipelines
3. **History** — Review historical changes and audit logs
4. **OCR Results** — View, validate, and export extracted data

---

## Technical Architecture & Core Features

### 1. Document Ingestion & Tenant Storage

- **Batch Processing** — Supports batch uploads of up to 10 files simultaneously (JPG, JPEG, PNG, PDF), capped at 10MB per file.
- **Tenant Isolation** — Uploaded files and rendered pages are securely isolated on disk within tenant-scoped directory structures (`storage/uploads/{username}/`).
- **Format Normalization** — Automatically converts multi-page PDFs into high-resolution discrete page images during ingestion.

### 2. Quality Profiling & Preprocessing Pipelines

Documents undergo automated quality assessment to evaluate blur (Laplacian variance), brightness, contrast, skew angle, and resolution. The system routes pages to one of seven targeted enhancement pipelines, which can be manually overridden via the frontend:

| Pipeline | Description |
|---|---|
| **Original** | Raw image pass-through |
| **Basic** | Standard grayscale conversion and bilateral denoising |
| **Low Light** | CLAHE histogram equalization and adaptive thresholding for underexposed text |
| **Overexposed** | Attenuation for bright/glare images |
| **Skewed** | Automated text contour angle detection and perspective deskewing |
| **Noisy Scan** | Median filtering and morphological operations to clear scanning artifacts |
| **Small Text** | Bicubic upscaling and unsharp masking for low-resolution prints |

### 3. Multi-Engine OCR & Extraction

- **Execution** — Orchestrates parallel text extraction across Tesseract, EasyOCR, and PaddleOCR engines.
- **Consensus & Scoring** — Calculates normalized scores based on engine confidence, text completeness, cross-engine Jaccard agreement, and speed.
- **Structured Data** — Extracts structured metadata (vendor info, invoice numbers, dates) and groups spatial tokens into rows and columns to reconstruct line-item tables.

### 4. Validation, Review, & Database

- **Business Rules** — Enforces mathematical validation (e.g., Subtotal + Tax = Grand Total) and flags anomalies.
- **Human-in-the-Loop Review** — Streamlit UI provides side-by-side original/enhanced page rendering, editable field input forms, and historical change audit logging.
- **Database Scalability** — Implemented via SQLAlchemy 2.0 ORM. Defaults to SQLite for immediate development but is scalable to PostgreSQL by modifying a single database connection string.
- **Security** — Employs simple, secure bcrypt password hashing for user accounts.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python, FastAPI |
| **Frontend UI** | Streamlit (Decoupled Client) |
| **Database & ORM** | SQLite / PostgreSQL, SQLAlchemy 2.0 |
| **Data Validation** | Pydantic v2 |
| **OCR Engines** | Tesseract, EasyOCR, PaddleOCR |
| **Image & PDF Processing** | OpenCV (cv2), Pillow (PIL), PyMuPDF |
| **Security** | bcrypt password hashing |
| **Package Manager** | uv |

---

## Project Directory Structure

```
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── document_routes.py
│   │           ├── history_routes.py
│   │           ├── ocr_routes.py
│   │           └── preprocess_routes.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── document_model.py
│   │   ├── ocr_model.py
│   │   └── user_model.py
│   ├── schemas/
│   │   ├── document_schema.py
│   │   ├── history_schema.py
│   │   ├── ocr_schema.py
│   │   ├── quality_schema.py
│   │   └── user_schema.py
│   ├── services/
│   │   ├── export_services.py
│   │   ├── extraction/
│   │   ├── ocr/
│   │   ├── preprocessing/
│   │   ├── validation/
│   │   ├── orchestrator.py
│   │   └── storage.py
│   └── main.py
├── frontend/
│   ├── app.py
│   ├── config.py
│   ├── utils/
│   │   ├── api.py
│   │   └── state.py
│   └── views/
│       ├── auth_view.py
│       ├── history_view.py
│       ├── ingestion_view.py
│       ├── ocr_view.py
│       ├── preprocessing_view.py
│       └── sidebar_view.py
├── storage/
│   └── uploads/
├── ocr_platform.db
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Installation & Setup

This project uses [`uv`](https://github.com/astral-sh/uv) for lightning-fast Python package management. A `uv.lock` file is included to guarantee deterministic dependency resolution.

### 1. Clone & Set Up Environment

```bash
git clone <repository-url>
cd ocr_document_intelligence

# Install all dependencies automatically using the lockfile
uv sync
```

### 2. Database Initialization

The SQLite database (`ocr_platform.db`) and tables are initialized automatically upon backend startup via SQLAlchemy 2.0 ORM models.

---

## Running the Application

The decoupled architecture requires running the FastAPI backend and Streamlit frontend concurrently, in separate terminal windows. It is highly recommended to run both services via `uv`.

**Terminal 1: FastAPI Backend**

```bash
uv run -m fastapi dev app/main.py
```

- API URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Terminal 2: Streamlit Frontend**

```bash
uv run -m streamlit run frontend/app.py
```

- Web UI: [http://localhost:8501](http://localhost:8501)

---

## Core API Endpoints

### System & Auth

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Root / Health Check |
| `POST` | `/api/v1/auth/register` | Register User |
| `POST` | `/api/v1/auth/login` | Login User |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload Document |
| `GET` | `/api/v1/documents/` | List Documents |
| `GET` | `/api/v1/documents/{document_id}` | Get Document |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete Document |
| `GET` | `/api/v1/documents/{document_id}/pages/{page_number}/image` | Get Page Image |

### Image Preprocessing

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/preprocessing/documents/{document_id}/pages/{page_number}` | Preprocess a single page |
| `POST` | `/api/v1/preprocessing/documents/{document_id}` | Batch preprocess all document pages |
| `GET` | `/api/v1/preprocessing/documents/{document_id}/pages/{page_number}/quality` | Get page quality report |
| `GET` | `/api/v1/preprocessing/documents/{document_id}/pages/{page_number}/processed-image` | Serve processed PNG image file |

### OCR & Extraction

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/ocr/{document_id}/process` | Process Document |
| `GET` | `/api/v1/ocr/{document_id}/status` | Get Document Status |
| `GET` | `/api/v1/ocr/{document_id}/result` | Get Document Result |
| `PUT` | `/api/v1/ocr/{document_id}/review` | Save Human Review |
| `GET` | `/api/v1/ocr/{document_id}/export` | Export Document Data |
| `GET` | `/api/v1/ocr/metrics/summary` | Get Metrics Summary |
| `POST` | `/api/v1/ocr/extract/raw` | Extract From Raw Payload |
| `POST` | `/api/v1/ocr/documents/{document_id}/extract` | Extract By Document Id |
| `GET` | `/api/v1/ocr/documents/{document_id}/structured-text` | Get Document Structured Text |

### History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/history` | Get Document History |
| `GET` | `/api/v1/history/history` | Get Detailed Document History |

---

## Contributing

Contributions are welcome! Please open an issue to discuss proposed changes, or submit a pull request with a clear description of the improvement.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.