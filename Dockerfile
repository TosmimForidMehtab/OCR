FROM python:3.14-slim

# Install system dependencies AND build tools needed to compile wheels
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements and project files
COPY . /app

# Upgrade pip and core build tools before installing your project
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir .

# Pre-download OCR models during build to avoid slow startup
RUN python -c "import easyocr; easyocr.Reader(['en', 'hi', 'mr'], gpu=False)"

# Expose the port FastAPI will run on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]