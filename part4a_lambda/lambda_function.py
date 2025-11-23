import requests
import json
import re
from datetime import datetime
import boto3
import logging
import os

BLS_URL = os.environ["BLS_URL"]
POP_URL = os.environ["POP_URL"]
S3_BLS_KEY_PREFIX = os.environ["S3_BLS_KEY_PREFIX"]
S3_POP_KEY = os.environ["S3_POP_KEY"]
S3_BUCKET = os.environ["S3_BUCKET"]
EMAIL = os.environ["EMAIL"]
SQS_URL = os.environ["SQS_URL"]

s3 = boto3.client(
    "s3",
    region_name="us-east-1"
)
sqs = boto3.client("sqs")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_bls_files():
    html = requests.get(BLS_URL, headers={"User-Agent": EMAIL}).text
    pattern = r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M).*?<A HREF="[^"]+">([^<]+)</A>'
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)

    bls_files = {}
    for date, time, filename in matches:
        dt = datetime.strptime(f"{date} {time}", "%m/%d/%Y %I:%M %p")
        bls_files[filename] = dt
    return bls_files

def get_s3_files():
    s3_files = {}
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_BLS_KEY_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.replace(S3_BLS_KEY_PREFIX, "")
            dt = obj["LastModified"].replace(tzinfo=None)
            s3_files[filename] = dt

    return s3_files 

def upload_file(filename):
    logger.info(f"Uploading {filename}…")
    file_bytes = requests.get(BLS_URL + filename, headers={"User-Agent": EMAIL}).content
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_BLS_KEY_PREFIX}{filename}",
        Body=file_bytes,
        ContentType="text/plain"
    )
    logger.info(f"{filename} successfully uploaded!")

def delete_file(filename):
    key = f"{S3_BLS_KEY_PREFIX}{filename}"
    logger.info(f"Deleting file: {filename}")
    s3.delete_object(Bucket=S3_BUCKET, Key=key)

def main_bls():
    bls_files = get_bls_files()
    s3_files = get_s3_files()

    for bls_f, bls_dt in bls_files.items():
        if bls_f not in s3_files.keys():
            logger.info(f"\nNew file found: {bls_f}")
            upload_file(bls_f)

        elif bls_dt > s3_files[bls_f]:
            logger.info(f"\nUpdated file detected: {bls_f}\n"
                f"Last updated in S3: {s3_files[bls_f]}\n"
                f"Last updated by BLS: {bls_dt}"
            )
            upload_file(bls_f)

        else:
            logger.info(f"\n{bls_f} is up to date.\n"
                f"Last updated in S3: {s3_files[bls_f]}\n"
                f"Last updated by BLS: {bls_dt}\n"
                "Skipping..."
            )

    for s3_f in s3_files.keys():
        if s3_f not in bls_files.keys():
            logger.info(f"\nFile removed by BLS: {bls_f}")
            delete_file(s3_f)

    logger.info("\nDone!")

def fetch_data():
    response = requests.get(POP_URL)
    response.raise_for_status()
    return response.json()


def upload_json_to_s3(data):
    body = json.dumps(data).encode("utf-8")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_POP_KEY,
        Body=body,
        ContentType="application/json"
    )

    logger.info(f"Uploaded {S3_POP_KEY} to s3://{S3_BUCKET}/{S3_POP_KEY}")
    
    message = {
        "s3_key": f"{S3_BUCKET}/{S3_POP_KEY}",
        "bucket": S3_BUCKET,
        "timestamp": datetime.utcnow().isoformat()
    }

    sqs.send_message(
        QueueUrl=SQS_URL,
        MessageBody=str(message)
    )
    logger.info(f"SQS message sent")


def main_pop():
    data = fetch_data()
    upload_json_to_s3(data)

def lambda_handler(event, context):
    main_bls()
    main_pop()
    return {
        'statusCode': 200,
        'body': json.dumps('Files updated successfully!')
    }

