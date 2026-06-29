resource "aws_apigatewayv2_api" "query_api" {
  name          = "rag-query-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://rag-chat-ui.pages.dev", "http://localhost:3000"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization", "*"]
    max_age       = 3600
  }
}

# Lambda integration
resource "aws_apigatewayv2_integration" "query_integration" {
  api_id                 = aws_apigatewayv2_api.query_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query.invoke_arn
  payload_format_version = "2.0"
}

# POST /query route
resource "aws_apigatewayv2_route" "query_route" {
  api_id    = aws_apigatewayv2_api.query_api.id
  route_key = "POST /query"
  target    = "integrations/${aws_apigatewayv2_integration.query_integration.id}"
}

# Auto deploy stage
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.query_api.id
  name        = "$default"
  auto_deploy = true
}

# Allow API Gateway to invoke query Lambda
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.query_api.execution_arn}/*/*"
}