import argparse
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

import boto3
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, NotFoundError, BadRequestError

from text_extractor import extract_text_from_file

load_dotenv()

# MinIO config
BUCKET_NAME = os.getenv("BUCKET_NAME", "default-bucket")
ENDPOINT = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")

# Elasticsearch config
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "epstein_docs")

es = Elasticsearch(
    ES_HOST,
    request_timeout=60,
    retry_on_timeout=True,
    max_retries=5,
)

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

es = Elasticsearch(ES_HOST)


# --- LOG TYPES ---
# Info: General information messages
# OK: Successful operations
# ERROR: Errors encountered during processing

def create_index_if_not_exists() -> None:
    """
    Checks if the Elasticsearch index exists, and creates it if not.
    """
    try:
        es.indices.get(index=ES_INDEX)
        print(f"[INFO] Index '{ES_INDEX}' already exists. No action needed.")
    except NotFoundError:
        # Explicit "index not found" from ES client
        print(f"[INFO] Index '{ES_INDEX}' not found, creating it.")
        es.indices.create(index=ES_INDEX)
        print(f"[INFO] Created index '{ES_INDEX}'.")
    except BadRequestError as e:
        es.indices.create(index=ES_INDEX)
        print(f"[INFO] Created index '{ES_INDEX}'.")


def is_supported(key: str) -> bool:
    """
    True if the object is a supported image
    """
    ext = os.path.splitext(key)[1].lower()
    return ext in [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"]


def list_bucket_keys(bucket: str) -> list[str]:
    """List all object keys in the MinIO bucket."""
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


def process_object(bucket: str, key: str) -> Optional[dict]:
    """Download object from MinIO, run text extraction, return result dict."""
    if not is_supported(key):
        return None

    suffix = os.path.splitext(key)[1]

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        # download from minio and save to a temporary file (needed bc extracter works on file paths)
        s3.download_fileobj(bucket, key, tmp)
        tmp.flush()
        # run text extraction
        extracted = extract_text_from_file(tmp.name)
        if extracted is None:
            return None

        result = {
            "key": key,
            "filename": os.path.basename(key),
            "filetype": extracted.get("filetype"),
            "content": extracted.get("text", ""),
        }

        return result


def index_document(result: dict) -> None:
    """
    Index the document into Elasticsearch.
    """
    doc_id = result['key']
    es.index(index=ES_INDEX, id=doc_id, document=result)
    print(f"[OK] Indexed to ES: {doc_id}")


def _worker_process(key: str) -> Optional[dict]:
    try:
        return process_object(BUCKET_NAME, key)
    except Exception as e:
        print(f"[ERROR] Failed to process {key}: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=max(os.cpu_count() or 1, 1),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()
    workers = max(args.workers, 1)

    print(f"Connecting to MinIO at {ENDPOINT} (bucket={BUCKET_NAME})")
    print(f"Connecting to Elasticsearch at {ES_HOST} (index={ES_INDEX})")
    print(f"Using {workers} worker process(es)")

    # Make sure the ES index exists
    create_index_if_not_exists()

    # List all objects in the bucket
    all_keys = list_bucket_keys(BUCKET_NAME)
    total_objects = len(all_keys)

    # keep only images
    keys = [k for k in all_keys if is_supported(k)]

    # use limit when testing
    if args.limit is not None:
        keys = keys[: args.limit]

    print(f"[INFO] Found {total_objects} objects in bucket.")
    print(f"[INFO] {len(keys)} objects are valid and will be processed.")

    if not keys:
        print("[INFO] There are no valid objects to process. Nothing to do.")
        return

    processed_count = 0

    if workers == 1:
        for key in keys:
            print(f"[INFO] Processing: {key}")
            result = _worker_process(key)
            if result is not None:
                index_document(result)
                processed_count += 1
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for result in executor.map(_worker_process, keys, chunksize=10):
                if result is None:
                    continue
                index_document(result)
                processed_count += 1

    print(
        f"[INFO] Finished. From {len(keys)} supported keys, successfully processed {processed_count} objects."
    )


if __name__ == "__main__":
    main()
