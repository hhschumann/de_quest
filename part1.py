import requests
import re
from datetime import datetime
import boto3
from dotenv import load_dotenv
import os
load_dotenv()

ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("SECRET_ACCESS_KEY")
EMAIL = os.getenv("EMAIL")
BASE_URL = "https://download.bls.gov/pub/time.series/pr/"
S3_BUCKET = "s3-rearc-quest-hs"
S3_PREFIX = "bls/pr/" 

s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name="us-east-1"
)

def get_bls_files():
    html = requests.get(BASE_URL, headers={"User-Agent": EMAIL}).text
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
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            filename = key.replace(S3_PREFIX, "")
            dt = obj["LastModified"].replace(tzinfo=None)
            s3_files[filename] = dt

    return s3_files 

def upload_file(filename):
    print(f"Uploading {filename}…")
    file_bytes = requests.get(BASE_URL + filename, headers={"User-Agent": EMAIL}).content
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_PREFIX}{filename}",
        Body=file_bytes,
        ContentType="text/plain"
    )
    print(f"{filename} successfully uploaded!")

def delete_file(filename):
    key = f"{S3_PREFIX}{filename}"
    print(f"Deleting file: {filename}")
    s3.delete_object(Bucket=S3_BUCKET, Key=key)

def main():
    bls_files = get_bls_files()
    s3_files = get_s3_files()

    for bls_f, bls_dt in bls_files.items():
        if bls_f not in s3_files.keys():
            print(f"\nNew file found: {bls_f}")
            upload_file(bls_f)

        elif bls_dt > s3_files[bls_f]:
            print(f"\nUpdated file detected: {bls_f}\n"
                f"Last updated in S3: {s3_files[bls_f]}\n"
                f"Last updated by BLS: {bls_dt}"
            )
            upload_file(bls_f)

        else:
            print(f"\n{bls_f} is up to date.\n"
                f"Last updated in S3: {s3_files[bls_f]}\n"
                f"Last updated by BLS: {bls_dt}\n"
                "Skipping..."
            )
        print(f"View file here: https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{S3_PREFIX}{bls_f}")

    for s3_f in s3_files.keys():
        if s3_f not in bls_files.keys():
            print(f"\nFile removed by BLS: {bls_f}")
            delete_file(s3_f)

    print("\nDone!")

if __name__ == "__main__":
    main()
