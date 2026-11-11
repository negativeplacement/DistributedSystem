Distributed Processing Pipeline
================================================

This document explains how to install, configure, and run the full pipeline
(MinIO, Text Extraction, Elasticsearch, Kibana).

## 1. Environment Setup

### 1.1 Create your .env file

Copy the example:
    ```cp .env.example .env```

Open ```.env``` and replace the placeholder values with your own.
Set the absolute path to the dataset directory.


## 2. Start Docker Services
From the project root:
```
docker compose up -d
```
**This starts MinIO, Elasticsearch, Kibana.**


## 3. Python and System Dependencies

### Use Python 3.11. Example on macOS:
```
python3.11 -m venv .venv 
source .venv/bin/activate 
```

### Install Tesseract OCR:
    brew install tesseract

### Install Python dependencies:
    pip install -r requirements.txt


## 4. Ingest Files into MinIO

### Run the ingestion script:
    python ingest.py

**This uploads dataset files into MinIO.**


## 5. Process Files and Index Into Elasticsearch

Run text extraction and indexing with multiple workers:
```
python process_minio_elasticsearch.py -w 4
```
Optional: limit to a subset of files:
```   
python process_minio_elasticsearch.py -w 4 --limit 100
```

## 6. Access Dashboards

**Kibana:
    http://localhost:5601**

**Elasticsearch:
    http://localhost:9200**

**MinIO:
    http://localhost:9000**  
(Use the credentials from .env)

