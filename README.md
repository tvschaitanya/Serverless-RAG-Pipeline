```markdown
# Serverless RAG Pipeline

A fully serverless retrieval-augmented generation (RAG) pipeline on AWS. Point it at any website, it crawls and indexes the content, and exposes a REST API that answers natural language questions about it with source citations.

---

## How It Works

**Ingestion** — crawls a target URL, chunks the content, embeds it with Cohere, and stores vectors in Weaviate.

**Query** — takes a natural language question, embeds it, retrieves the most relevant chunks from Weaviate, and generates an answer with Claude Haiku via Bedrock. Every request is traced in Langfuse.

```
Ingestion:
Firecrawl → Lambda → Bedrock (Cohere Embed v3) → Weaviate Cloud

Query:
API Gateway → Lambda → Bedrock (Cohere Embed v3) → Weaviate → Bedrock (Claude Haiku) → JSON response
                                                                                      ↓
                                                                                  Langfuse
```

---

## Stack

| Layer | Service |
|---|---|
| Web crawling | Firecrawl |
| Embeddings | AWS Bedrock — Cohere Embed English v3 |
| Vector database | Weaviate Cloud (free tier) |
| LLM | AWS Bedrock — Claude Haiku 4.5 |
| Compute | AWS Lambda (Python 3.12) |
| API | AWS API Gateway HTTP API |
| Observability | Langfuse |
| IaC | Terraform |

---

## Project Structure

```
.
├── lambdas/
│   ├── ingest/
│   │   ├── handler.py        # crawl, chunk, embed, store
│   │   └── requirements.txt
│   └── query/
│       ├── handler.py        # embed query, retrieve, generate, trace
│       └── requirements.txt
├── main.tf                   # provider and region
├── variables.tf              # all input variables
├── outputs.tf                # API URL and Lambda name
├── iam.tf                    # Lambda role with Bedrock and Marketplace permissions
├── lambda.tf                 # ingest and query Lambda functions
├── apigateway.tf             # HTTP API Gateway with POST /query route and rate limiting
├── terraform.tfvars.example  # template for your secrets
└── README.md
```

---

## Prerequisites

Before you start you need:

- **AWS account** with an IAM user (not root) that has admin access
- **AWS CLI** installed and configured (`aws configure`)
- **Terraform** >= 1.3.0
- **Python** 3.12
- **uv** package manager (`pip install uv`)
- **Firecrawl account** — [firecrawl.dev](https://firecrawl.dev) (free tier works)
- **Weaviate Cloud account** — [console.weaviate.cloud](https://console.weaviate.cloud) (free tier works)
- **Langfuse account** — [cloud.langfuse.com](https://cloud.langfuse.com) (free tier works)

---

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd <repo>
```

### 2. Install Lambda dependencies

Dependencies must be installed targeting Linux x86_64 even if you're on Mac or Windows — Lambda runs on Linux.

```bash
uv pip install -r lambdas/ingest/requirements.txt \
  --target lambdas/ingest/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python 3.12

uv pip install -r lambdas/query/requirements.txt \
  --target lambdas/query/ \
  --python-platform x86_64-unknown-linux-gnu \
  --python 3.12
```

### 3. Configure secrets

```bash
cp terraform.tfvars.example terraform.tfvars
```

Fill in your values:

```hcl
aws_region        = "us-east-1"
firecrawl_api_key = "your-firecrawl-api-key"
weaviate_url      = "your-weaviate-cluster-url"
weaviate_api_key  = "your-weaviate-api-key"
target_url        = "https://yoursite.com/"
crawl_limit       = 10
collection_name   = "YourSitePages"

# Langfuse
langfuse_public_key = "pk-lf-..."
langfuse_secret_key = "sk-lf-..."
langfuse_host       = "https://cloud.langfuse.com"  # or https://us.cloud.langfuse.com for US region
```

**Notes:**
- `terraform.tfvars` is gitignored — never commit it
- `collection_name` must start with an uppercase letter and contain only letters and numbers — no hyphens or underscores (e.g. `Mysite` not `my-site`)
- `crawl_limit` controls how many pages Firecrawl fetches — start with 10 and increase once everything works
- For Langfuse, use `https://us.cloud.langfuse.com` if your project is in the US region, otherwise `https://cloud.langfuse.com`

### 4. Enable Cohere model access on Bedrock

Cohere Embed requires a one-time AWS Marketplace agreement per account. Run these two commands:

```bash
aws bedrock list-foundation-model-agreement-offers \
  --model-id cohere.embed-english-v3
```

Copy the `offerToken` from the output, then:

```bash
aws bedrock create-foundation-model-agreement \
  --model-id cohere.embed-english-v3 \
  --offer-token <offer-token-from-above>
```

You also need to enable **Claude Haiku** in the Bedrock console under Model Access if you haven't already.

### 5. Deploy

```bash
terraform init
terraform apply -auto-approve
```

Terraform will output the API URL when done:

```
query_api_url      = "https://xxxx.execute-api.us-east-1.amazonaws.com/query"
ingest_lambda_name = "rag-ingest"
```

### 6. Run ingestion

This crawls your target URL and loads everything into Weaviate. Run it once after deploy, and re-run any time you want to refresh the data.

```bash
aws lambda invoke --function-name rag-ingest --log-type Tail output.json \
  --query 'LogResult' --output text | base64 -d
```

You'll see logs showing pages crawled and chunks stored. Re-running ingestion is safe — it wipes and rebuilds the collection every time.

### 7. Query

```bash
curl -X POST https://xxxx.execute-api.us-east-1.amazonaws.com/query \
  -H "Content-Type: application/json" \
  -d '{"question": "what does this site offer?"}'
```

Response:

```json
{
  "answer": "...",
  "sources": [
    "https://yoursite.com/page-1",
    "https://yoursite.com/page-2"
  ]
}
```

### 8. View traces in Langfuse

Every query is traced automatically. Go to [cloud.langfuse.com](https://cloud.langfuse.com) → your project → **Tracing** to see each request with its input question, answer, and sources.

---

## Rate Limiting

The API Gateway is configured to allow 10 requests per second with a burst limit of 20. Requests exceeding this return a `429 Too Many Requests` response. Adjust `throttling_rate_limit` and `throttling_burst_limit` in `apigateway.tf` to tune for your use case.

---

## Changing the target site

Update `target_url` and `collection_name` in `terraform.tfvars`, redeploy, then re-run ingestion:

```bash
terraform apply -auto-approve
aws lambda invoke --function-name rag-ingest --log-type Tail output.json \
  --query 'LogResult' --output text | base64 -d
```

---

## Debugging

Check Lambda logs in real time:

```bash
aws logs tail /aws/lambda/rag-ingest --follow
aws logs tail /aws/lambda/rag-query --follow
```

---

## Common issues

| Error | Fix |
|---|---|
| `could not find class X in schema` | Ingestion hasn't run yet, or `collection_name` changed — re-run ingest |
| `expected maxLength: 2048` | Chunks are too long — reduce `chunk_size` in `lambdas/ingest/handler.py` to 70 |
| `ResourceNotFoundException` on Bedrock | Enable the model in AWS Bedrock console under Model Access |
| `AuthenticationFailedException` on Weaviate | Double-check `weaviate_url` and `weaviate_api_key` in tfvars |
| `Invalid JSON` from query API | Ensure `Content-Type: application/json` header is set |
| `500 Internal Server Error` | Check query Lambda logs — almost always a Bedrock or Weaviate config issue |
| `429 Too Many Requests` | Rate limit hit — back off and retry |
| Traces not appearing in Langfuse | Check `langfuse_host` — use `https://us.cloud.langfuse.com` for US region projects |

---

## Cost

Fully serverless — you pay per invocation, not uptime.

| Service | Est. cost at 2000 queries/month |
|---|---|
| Lambda | $0 (free tier) |
| API Gateway | ~$0.002 |
| Bedrock (Cohere + Haiku) | ~$0.20 |
| Weaviate Cloud | $0 (free tier) |
| Langfuse | $0 (free tier) |
| **Total** | **under $0.25/month** |

---

## Teardown

```bash
terraform destroy -auto-approve
```

Removes all AWS resources. Your Weaviate, Firecrawl, and Langfuse accounts are unaffected and must be managed separately.

---

## Important notes

- Lambda dependencies must target Linux x86_64 regardless of your local OS
- Cohere Embed requires a one-time AWS Marketplace agreement per AWS account
- Claude Haiku must be invoked using the `us.` inference profile prefix for cross-region routing
- The Weaviate client is instantiated inside the Lambda handler, not at module level — this is intentional to avoid stale connections on warm invocations
- Re-running ingestion wipes and rebuilds the Weaviate collection — existing data is replaced
- `collection_name` must be PascalCase with no special characters — Weaviate enforces this
- Langfuse SDK must be pinned to v2 (`langfuse>=2.0.0,<3.0.0`) — v3 uses a different API
- Context sent to Bedrock is capped at 3 chunks and 3000 characters to control input token costs
```