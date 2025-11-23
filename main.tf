terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.3.0"
}

provider "aws" {
  region = "us-east-1"
}

# ------------------------------
# S3 Bucket
# ------------------------------
resource "aws_s3_bucket" "s3_quest_bucket" {
  bucket        = "s3-rearc-quest-hs"
  force_destroy = true
}

# ------------------------------
# S3 Bucket Access
# ------------------------------
resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket = aws_s3_bucket.s3_quest_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_read" {
  bucket = aws_s3_bucket.s3_quest_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.s3_quest_bucket.arn}/*"
      }
    ]
  })
}

# ------------------------------
# Python Layer S3 Bucket
# ------------------------------

resource "aws_s3_bucket" "s3_lambda_layers" {
  bucket = "s3-rearc-lambda-layers-hs"
  force_destroy = true
}

resource "aws_s3_object" "lambda_layer" {
  bucket = aws_s3_bucket.s3_lambda_layers.bucket
  key    = "layers/requests-layer.zip"
  source = "python_layer/requests_layer.zip"
  etag   = filemd5("python_layer/requests_layer.zip")
}

# ------------------------------
# Python Layer
# ------------------------------

resource "aws_lambda_layer_version" "requests_layer" {
  layer_name  = "requests-layer"
  s3_bucket   = aws_s3_bucket.s3_lambda_layers.bucket
  s3_key      = aws_s3_object.lambda_layer.key
  compatible_runtimes = ["python3.13"]
}

# ------------------------------
# SQS Queue
# ------------------------------
resource "aws_sqs_queue" "data_sqs_queue" {
  name                       = "ingestion-finished"
  visibility_timeout_seconds = 60
}

# ------------------------------
# IAM Role for Lambda
# ------------------------------
resource "aws_iam_role" "lambda_role" {
  name = "shared-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "shared-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch logs
      {
        Effect   = "Allow"
        Action   = ["logs:*"]
        Resource = "*"
      },
      # S3 upload permission
      {
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = "${aws_s3_bucket.s3_quest_bucket.arn}"
      },
      # S3 upload permission
      {
        Effect = "Allow"
        Action = ["s3:*"]
        Resource = "${aws_s3_bucket.s3_quest_bucket.arn}/*"
      },
      # SQS SendMessage permission
      {
        Effect   = "Allow"
        Action   = ["sqs:*"]
        Resource = aws_sqs_queue.data_sqs_queue.arn
      }
    ]
  })
}

# ------------------------------
# Package Ingestion Lambda
# ------------------------------
data "archive_file" "ingestion_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/part4a_lambda"
  output_path = "${path.module}/part4a_lambda.zip"
}

# ------------------------------
# Lambda Ingestion Function
# ------------------------------
resource "aws_lambda_function" "ingestion_lambda" {
  function_name = "data-ingestion"
  runtime       = "python3.13"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.ingestion_lambda_zip.output_path
  source_code_hash = data.archive_file.ingestion_lambda_zip.output_base64sha256

  timeout = 60

  layers = [
    aws_lambda_layer_version.requests_layer.arn
  ]

  environment {
    variables = {
      BLS_URL           = "https://download.bls.gov/pub/time.series/pr/"
      POP_URL           = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
      EMAIL             = "hhschumann1@gmail.com"
      S3_BLS_KEY_PREFIX = "bls/pr/"
      S3_BUCKET         = "s3-rearc-quest-hs"
      S3_POP_KEY        = "datausa/population.json"
      SQS_URL           = aws_sqs_queue.data_sqs_queue.id
    }
  }
}

# ------------------------------
# Package Processing Lambda
# ------------------------------
data "archive_file" "processing_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/part4b_lambda"
  output_path = "${path.module}/part4b_lambda.zip"
}

# ------------------------------
# Lambda Processing Function
# ------------------------------
resource "aws_lambda_function" "processing_lambda" {
  function_name = "data-processing"
  runtime       = "python3.13"
  handler       = "lambda_function.lambda_handler"
  role          = aws_iam_role.lambda_role.arn

  filename         = data.archive_file.processing_lambda_zip.output_path
  source_code_hash = data.archive_file.processing_lambda_zip.output_base64sha256

  timeout = 60

  layers = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python313:5"]

  environment {
    variables = {
      S3_BLS_KEY_PREFIX = "bls/pr/"
      S3_BUCKET         = "s3-rearc-quest-hs"
      S3_POP_KEY        = "datausa/population.json"
      SQS_URL           = aws_sqs_queue.data_sqs_queue.id
    }
  }
}

# ------------------------------
# Daily CloudWatch Trigger
# ------------------------------
resource "aws_cloudwatch_event_rule" "daily" {
  name                = "ingestion-daily-trigger"
  description         = "Trigger data download daily"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "daily_target" {
  rule      = aws_cloudwatch_event_rule.daily.name
  target_id = "lambda"
  arn       = aws_lambda_function.ingestion_lambda.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

# ------------------------------
# SQS Queue Trigger
# ------------------------------

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn  = aws_sqs_queue.data_sqs_queue.arn
  function_name     = aws_lambda_function.processing_lambda.arn
  batch_size        = 10 
  enabled           = true
}
