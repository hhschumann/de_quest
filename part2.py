import requests
import boto3
import json
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("SECRET_ACCESS_KEY")
EMAIL = os.getenv("EMAIL")
URL = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
S3_BUCKET = "s3-rearc-quest-hs"
S3_KEY = "datausa/population.json" 

s3 = boto3.client(
    "s3",
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    region_name="us-east-1"
)

def fetch_data():
    response = requests.get(URL)
    response.raise_for_status()
    return response.json()


def upload_json_to_s3(data):
    body = json.dumps(data).encode("utf-8")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY,
        Body=body,
        ContentType="application/json"
    )
    print(f"Uploaded {S3_KEY} to s3://{S3_BUCKET}/{S3_KEY}")
    print(f"View file here: https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{S3_KEY}")
    

def main():
    data = fetch_data()
    upload_json_to_s3(data)


if __name__ == "__main__":
    main()
