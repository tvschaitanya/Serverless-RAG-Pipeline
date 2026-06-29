variable "aws_region" {
  default = "us-east-1"
}

variable "firecrawl_api_key" {
  description = "Firecrawl API key"
  type        = string
  sensitive   = true
}

variable "weaviate_url" {
  description = "Weaviate Cloud cluster URL"
  type        = string
}

variable "weaviate_api_key" {
  description = "Weaviate Cloud API key"
  type        = string
  sensitive   = true
}

variable "target_url" {
  description = "URL to crawl and ingest"
  type        = string
  default     = "https://ischool.cci.fsu.edu/"
}

variable "crawl_limit" {
  description = "Max pages to crawl"
  type        = number
  default     = 10
}