FROM python:3.14-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency definition first (for caching)
COPY pyproject.toml ./

# If you have a lock file, include it
# COPY poetry.lock ./
# COPY pdm.lock ./

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies from pyproject
RUN pip install --no-cache-dir .

# Now copy the rest of the app
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]