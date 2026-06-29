output "query_api_url" {
  description = "Public URL to query the RAG system"
  value       = "${aws_apigatewayv2_api.query_api.api_endpoint}/query"
}

output "ingest_lambda_name" {
  description = "Ingest Lambda name for manual invoke"
  value       = aws_lambda_function.ingest.function_name
}