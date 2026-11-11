import boto3
import os
import sys
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# 1. Load the variables from .env
load_dotenv()

# --- CONFIGURATION FROM ENV ---
LOCAL_SOURCE_FOLDER = os.getenv("LOCAL_DATA_FOLDER", "./default_data")
BUCKET_NAME = os.getenv("BUCKET_NAME", "default-bucket")
ENDPOINT = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")

# Note: We map MINIO_ROOT_USER to the AWS Access Key ID
ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "admin")
SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "password")

CREDS = {
    "aws_access_key_id": ACCESS_KEY,
    "aws_secret_access_key": SECRET_KEY
}

def get_client():
    return boto3.client('s3', endpoint_url=ENDPOINT, **CREDS)

def run():
    print(f"[INFO] Connecting to {ENDPOINT} as user '{ACCESS_KEY}'...")
    s3 = get_client()
    
    # Create Bucket
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' ready.")
    except ClientError as e:
        # Check if error is simply that bucket exists
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyOwnedByYou' or error_code == 'BucketAlreadyExists':
            print(f"[ERROR] Bucket '{BUCKET_NAME}' already exists.")
        else:
            print(f"[ERROR] Critical Error: {e}")
            return

    # Upload
    if not os.path.exists(LOCAL_SOURCE_FOLDER):
        print(f"[ERROR]: Folder '{LOCAL_SOURCE_FOLDER}' not found.")
        return

    print(f"[INFO] Uploading from: {LOCAL_SOURCE_FOLDER}")
    
    count = 0
    for root, _, files in os.walk(LOCAL_SOURCE_FOLDER):
        for file in files:
            local_path = os.path.join(root, file)
            s3_key = os.path.relpath(local_path, LOCAL_SOURCE_FOLDER)
            
            try:
                s3.upload_file(local_path, BUCKET_NAME, s3_key)
                print(f"[OK] Uploaded: {s3_key}")
                count += 1
            except Exception as e:
                print(f"[ERROR]: {e}")
    
    print(f"[INFO] Processed {count} files.")

if __name__ == "__main__":
    run()