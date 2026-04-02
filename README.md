# OCR Backend

Accepts a JPG/PNG image, extracts text via **EasyOCR**, and returns a **searchable PDF**
where all text is selectable. Supports **English**, **Hindi**, and **Marathi**.

---

## Requirements

- Python 3.14+
- `libmagic` (used by `python-magic` for MIME detection)

```bash
# macOS
brew install libmagic

# Debian / Ubuntu
sudo apt-get install libmagic1
```

---

## Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ocr-backend

# 2. Create and activate a virtual environment
python3.14 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Configure environment
cp .env.example .env
# Edit .env as needed

# 5. Add fonts (required for Hindi / Marathi PDF output)
#    Download NotoSans-Regular.ttf from https://fonts.google.com/noto/specimen/Noto+Sans
#    and place it at:
mkdir -p assets/fonts
cp ~/Downloads/NotoSans-Regular.ttf assets/fonts/
```

---

## Pre-download EasyOCR Models

EasyOCR downloads model weights on first use (~100–300 MB per language).
Run this once before starting the server to avoid a cold-start delay:

```bash
python - <<'EOF'
import easyocr
# Downloads models for all supported languages
easyocr.Reader(['en', 'hi', 'mr'], gpu=False, verbose=True)
print("Models ready.")
EOF
```

Models are cached in `~/.EasyOCR/`.

---

## Running

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:

```bash
uvicorn app.main:app --reload
```

For multi-worker production (OCR is CPU-bound):

```bash
uvicorn app.main:app --workers 4
```

---

## API

Interactive docs available at **http://localhost:8000/docs**.

### `GET /api/v1/health`

```json
{ "status": "ok", "version": "1.0.0" }
```

### `POST /api/v1/ocr/extract`

| Parameter | Location    | Type   | Required | Description                              |
|-----------|-------------|--------|----------|------------------------------------------|
| `file`    | form-data   | file   | Yes      | JPG or PNG image (max 10 MB by default)  |
| `langs`   | query param | string | No       | Comma-separated codes: `en`, `hi`, `mr` |

**Example (curl)**

```bash
curl -X POST "http://localhost:8000/api/v1/ocr/extract?langs=en,hi" \
  -F "file=@sample/input/invoice.jpg" \
  --output sample/output/invoice_ocr.pdf
```

**Response:** binary PDF with `Content-Disposition: attachment; filename="invoice_ocr.pdf"`.

---

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable                    | Default            | Description                              |
|-----------------------------|--------------------|------------------------------------------|
| `APP_HOST`                  | `0.0.0.0`          | Bind address                             |
| `APP_PORT`                  | `8000`             | Bind port                                |
| `OCR_DEFAULT_LANGS`         | `en`               | Default languages if `?langs=` is absent |
| `OCR_CONFIDENCE_THRESHOLD`  | `0.4`              | Minimum confidence to include a word     |
| `OCR_GPU`                   | `false`            | Enable CUDA GPU for EasyOCR              |
| `MAX_UPLOAD_SIZE_MB`        | `10`               | Maximum upload size in MB                |
| `TEMP_DIR`                  | `/tmp/ocr_uploads` | Directory for temporary files            |
| `LOG_LEVEL`                 | `INFO`             | `DEBUG`, `INFO`, `WARNING`, `ERROR`      |
| `LOG_FORMAT`                | `json`             | `json` or `text`                         |

---

## Project Structure

```
ocr-backend/
├── app/
│   ├── main.py                  # FastAPI app factory, lifespan
│   ├── api/v1/routes/ocr.py     # POST /api/v1/ocr/extract, GET /api/v1/health
│   ├── core/
│   │   ├── config.py            # Typed settings (pydantic-settings)
│   │   ├── exceptions.py        # Domain exceptions + FastAPI handlers
│   │   └── logging.py           # Structlog bootstrap
│   ├── models/schemas.py        # Pydantic models
│   ├── services/
│   │   ├── image_processor.py   # OpenCV/Pillow pre-processing pipeline
│   │   ├── ocr_service.py       # EasyOCR orchestration + layout assembly
│   │   └── pdf_generator.py     # ReportLab searchable PDF builder
│   └── utils/file_utils.py      # MIME validation, temp file helpers
├── assets/fonts/                # NotoSans TTF (Devanagari support)
├── sample/input/                # Example input images
├── sample/output/               # Example output PDFs
├── .env.example
├── pyproject.toml
└── README.md
```
