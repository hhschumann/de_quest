import json
import pandas as pd
from io import StringIO
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BLS_KEY_PREFIX = os.environ["S3_BLS_KEY_PREFIX"]
S3_POP_KEY = os.environ["S3_POP_KEY"]
S3_BUCKET = os.environ["S3_BUCKET"]

s3 = boto3.client(
    "s3",
    region_name="us-east-1"
)

def lambda_handler(event, context):
    # ---- Part 3.0 ----
    # population dataset
    response = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_POP_KEY}")
    pop_str = response['Body'].read().decode('utf-8')
    pop_data = json.loads(pop_str)['data']
    pop_df = pd.DataFrame(pop_data)

    # bls time series datasets
    response = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_BLS_KEY_PREFIX}pr.data.0.Current")
    file_content = response['Body'].read().decode('utf-8')
    bls_df = pd.read_csv(StringIO(file_content), sep='\t')

    # ---- Part 3.1 ----

    mean = pop_df['Population'].mean()
    std = pop_df['Population'].std()

    logger.info("="*10 + " Part 3.1: Mean & SD " + "-"*10)
    logger.info(f"Mean of US population: {mean:.2f}")
    logger.info(f"Standard deviation of US population: {std:.2f}")

    # ---- Part 3.2 ----

    bls_df.columns = [c.strip() for c in bls_df.columns]
    bls_df['series_id'] = bls_df['series_id'].str.rstrip()

    yearly_sums = bls_df.groupby(["series_id", "year"], as_index=False)["value"].sum()
    result = yearly_sums.loc[yearly_sums.groupby("series_id")["value"].idxmax()]
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    logger.info("="*10 + " Part 3.2: Best Years " + "-"*10)
    logger.info(result)

    # ---- Part 3.3 ----

    bls_filtered_df = bls_df[(bls_df['series_id'] == "PRS30006032") & (bls_df['period'] == 'Q01')]
    merged_df_inner = pd.merge(
        bls_filtered_df, 
        pop_df.rename(columns={'Year': 'year'}, inplace=False)[["year", "Population"]],
        on="year",
        how='left') 
    logger.info("="*10 + " Part 3.3: Merged Dataframe " + "-"*10)
    logger.info(merged_df_inner)

    return {
        'statusCode': 200,
        'body': json.dumps('Report run successfully!')
    }