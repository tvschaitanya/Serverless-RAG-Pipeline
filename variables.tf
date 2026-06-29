variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
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
  default     = ""
}

variable "crawl_limit" {
  description = "Max pages to crawl"
  type        = number
  default     = 10
}

variable "collection_name" {
  description = "Weaviate collection name for stored chunks"
  type        = string
  default     = "WebPages"
}

# --- Langfuse Variables ---

variable "langfuse_public_key" {
  description = "Langfuse Public API Key"
  type        = string
}

variable "langfuse_secret_key" {
  description = "Langfuse Secret API Key"
  type        = string
  sensitive   = true
}

variable "langfuse_host" {
  description = "Langfuse Host URL"
  type        = string
  default     = "https://cloud.langfuse.com"
}