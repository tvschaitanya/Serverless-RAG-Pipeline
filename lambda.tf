# Zip ingest Lambda
data "archive_file" "ingest" {
  type        = "zip"
  source_dir  = "lambdas/ingest"
  output_path = "ingest.zip"
}

# Zip query Lambda
data "archive_file" "query" {
  type        = "zip"
  source_dir  = "lambdas/query"
  output_path = "query.zip"
}

# Ingest Lambda
resource "aws_lambda_function" "ingest" {
  function_name    = "rag-ingest"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = "ingest.zip"
  source_code_hash = data.archive_file.ingest.output_base64sha256
  timeout          = 900
  memory_size      = 512

  environment {
    variables = {
      FIRECRAWL_API_KEY = var.firecrawl_api_key
      WEAVIATE_URL      = var.weaviate_url
      WEAVIATE_API_KEY  = var.weaviate_api_key
      TARGET_URL        = var.target_url
      AWS_REGION_NAME   = var.aws_region
      CRAWL_LIMIT       = tostring(var.crawl_limit)
      COLLECTION_NAME   = var.collection_name
    }
  }
}

# Query Lambda
resource "aws_lambda_function" "query" {
  function_name    = "rag-query"
  role             = aws_iam_role.lambda_role.arn
  runtime          = "python3.12"
  handler          = "handler.lambda_handler"
  filename         = "query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      WEAVIATE_URL        = var.weaviate_url
      WEAVIATE_API_KEY    = var.weaviate_api_key
      AWS_REGION_NAME     = var.aws_region
      COLLECTION_NAME     = var.collection_name
      
      # Langfuse Automatic SDK Configuration
      LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
      LANGFUSE_SECRET_KEY = var.langfuse_secret_key
      LANGFUSE_HOST       = var.langfuse_host
    }
  }
}