# Dockerfile - EngTeklif API with Full CadQuery Support
FROM python:3.11-slim

# Install system dependencies for CadQuery and Material Analysis
RUN apt-get update && apt-get install -y \
    # OpenGL and rendering libraries for CadQuery
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libfontconfig1 \
    libxrandr2 \
    libxss1 \
    libgtk-3-0 \
    libasound2 \
    # OCR and document processing
    tesseract-ocr \
    tesseract-ocr-tur \
    tesseract-ocr-eng \
    poppler-utils \
    # LibreOffice for DOC conversion
    libreoffice \
    # Virtual display for headless CadQuery
    xvfb \
    # Additional dependencies
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables for CadQuery
ENV DISPLAY=:99
ENV CADQUERY_DISABLE_JUPYTER=1
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV LIBREOFFICE_PATH=/usr/bin/libreoffice
ENV OPENCV_LOG_LEVEL=ERROR

# Create working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads static temp && \
    chmod 755 uploads static temp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Start script with Xvfb for CadQuery
CMD ["bash", "-c", "Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset & python -u app.py"]