# Dockerfile - EngTeklif API (macOS Apple Silicon Compatible)

# Multi-platform support for both x86_64 (Intel/AMD) and ARM64 (Apple Silicon)

# Force platform selection for compatibility

FROM --platform=linux/amd64 python:3.11-slim

# Set environment variables for cross-platform compatibility

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies

RUN apt-get update && apt-get install -y \

# Build tools

build-essential \
 pkg-config \
 gcc \
 g++ \

# OCR and document processing

tesseract-ocr \
 tesseract-ocr-tur \
 tesseract-ocr-eng \
 poppler-utils \

# LibreOffice for DOC conversion

libreoffice \

# System libraries for Python packages

libglib2.0-0 \
 libsm6 \
 libxext6 \
 libxrender-dev \
 libgomp1 \
 libfontconfig1 \

# Additional OpenCV dependencies

libgl1-mesa-glx \
 libglib2.0-0 \
 libgtk-3-0 \

# Network and utility tools

wget \
 curl \
 && rm -rf /var/lib/apt/lists/\*

# Set up environment variables

ENV TESSERACT_CMD=/usr/bin/tesseract
ENV LIBREOFFICE_PATH=/usr/bin/libreoffice
ENV OPENCV_LOG_LEVEL=ERROR

# Create working directory

WORKDIR /app

# Copy requirements first for better Docker layer caching

COPY requirements.txt .

# Install Python dependencies with specific flags for cross-platform

RUN pip install --upgrade pip setuptools wheel && \
 pip install --no-cache-dir --prefer-binary -r requirements.txt

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

# Start application

CMD ["python", "-u", "app.py"]

---

---

# requirements.txt - EngTeklif API (macOS Apple Silicon Compatible)

# Son güncelleme: 2025-01-01 - Material Analysis Integration - MACOS COMPATIBLE

# =============================================

# CORE FRAMEWORK

# =============================================

Flask==3.0.0
Flask-CORS==4.0.0
Flask-JWT-Extended==4.6.0
Werkzeug==3.0.1

# =============================================

# DATABASE & ODM

# =============================================

pymongo==4.6.1

# =============================================

# AUTHENTICATION & SECURITY

# =============================================

bcrypt==4.1.2
PyJWT==2.8.0
cryptography>=41.0.0,<46.0.0

# =============================================

# DATA VALIDATION & MODELING

# =============================================

pydantic==2.5.3
email-validator==2.1.0

# =============================================

# FILE PROCESSING & ANALYSIS (REQUIRED)

# =============================================

# PDF Processing

PyPDF2==3.0.1
pdf2image==1.17.0
pikepdf>=8.0.0,<9.0.0

# Document Processing

python-docx==1.1.0

# Image Processing - macOS compatible versions

Pillow>=10.0.0,<11.0.0

# Use headless version for better compatibility in Docker

opencv-python-headless>=4.8.0,<5.0.0

# OCR

pytesseract==0.3.10

# =============================================

# SCIENTIFIC COMPUTING

# =============================================

# Pin to versions with good ARM64 support

numpy>=1.24.0,<2.0.0
scipy>=1.10.0,<2.0.0
pandas>=2.0.0,<3.0.0

# =============================================

# VISUALIZATION (NO CAD FOR COMPATIBILITY)

# =============================================

matplotlib>=3.7.0,<4.0.0

# =============================================

# EXCEL & DATA EXPORT

# =============================================

openpyxl>=3.1.0,<4.0.0
xlsxwriter>=3.0.0,<4.0.0

# =============================================

# TEXT PROCESSING & FUZZY MATCHING

# =============================================

Levenshtein>=0.20.0
rapidfuzz>=3.0.0
fuzzywuzzy==0.18.0

# =============================================

# DOCUMENT PROCESSING

# =============================================

striprtf>=0.0.26

# =============================================

# WEBSOCKET SUPPORT

# =============================================

Flask-SocketIO>=5.3.0
python-socketio>=5.11.0

# =============================================

# GMAIL API

# =============================================

google-api-python-client>=2.100.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.2.0

# =============================================

# XML & HTML PROCESSING

# =============================================

lxml>=5.0.0
beautifulsoup4>=4.12.0

# =============================================

# SYSTEM INTEGRATION

# =============================================

psutil>=5.9.0

# =============================================

# NETWORKING & HTTP

# =============================================

requests>=2.28.0,<3.0.0

# =============================================

# UTILITIES

# =============================================

python-dotenv>=1.0.0
python-dateutil>=2.8.0
click>=8.0.0

# =============================================

# FILE HANDLING

# =============================================

python-magic>=0.4.24

# =============================================

# PRODUCTION SERVER

# =============================================

gunicorn>=21.0.0

# =============================================

# MACOS SPECIFIC NOTES

# =============================================

# Bu requirements.txt dosyası şu platformlar için optimize edilmiştir:

# - Windows x86_64 (Intel/AMD)

# - macOS x86_64 (Intel Mac)

# - macOS ARM64 (Apple Silicon M1/M2)

# - Linux x86_64

# - Linux ARM64

#

# Önemli değişiklikler:

# 1. opencv-python -> opencv-python-headless (GUI bağımlılıkları olmadan)

# 2. CadQuery kaldırıldı (ARM64 uyumluluk sorunları nedeniyle)

# 3. open3d kaldırıldı (büyük bağımlılık)

# 4. Paket versiyonları ARM64 desteği olan versiyonlara sabitlendi

# =============================================
