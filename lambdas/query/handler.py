import os
import json
import boto3
import weaviate
from weaviate.classes.init import Auth
from langfuse import Langfuse

COLLECTION_NAME = os.environ["COLLECTION_NAME"]

def get_bedrock():
    return boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION_NAME"])

def embed_query(bedrock, text):
    response = bedrock.invoke_model(
        modelId="cohere.embed-english-v3",
        body=json.dumps({
            "texts": [text],
            "input_type": "search_query"
        })
    )
    return json.loads(response["body"].read())["embeddings"][0]  # Fixed: was missing [0]

def retrieve(client, bedrock, question):
    vector = embed_query(bedrock, question)
    collection = client.collections.get(COLLECTION_NAME)
    results = collection.query.near_vector(
        near_vector=vector,
        limit=5,
        return_properties=["text", "source"]
    )
    return results.objects

def generate(bedrock, question, chunks):
    if not chunks:
        return "I don't have enough information to answer that question.", []

    context = "\n\n".join([obj.properties["text"] for obj in chunks])
    sources = list(set([obj.properties["source"] for obj in chunks]))

    prompt = f"""You are a helpful assistant.
Use only the context below to answer the question.
If the context does not contain enough information, say so clearly.

Context:
{context}

Question: {question}
Answer:"""

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    body = json.loads(response["body"].read())
    return body["content"][0]["text"], sources  # Fixed: was body["content"]["text"]

def lambda_handler(event, context):
    client = None
    langfuse = Langfuse(flush_at=1)

    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {"statusCode": 200, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON"})}

    question = (body.get("question") or "").strip()
    if not question:
        return {"statusCode": 400, "body": json.dumps({"error": "question is required"})}

    if len(question) > 1000:
        return {"statusCode": 400, "body": json.dumps({"error": "question must be under 1000 characters"})}

    trace = langfuse.trace(name="rag-query-request", input={"question": question})

    try:
        print(f"Question: {question}")
        bedrock = get_bedrock()

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=os.environ["WEAVIATE_URL"],
            auth_credentials=Auth.api_key(os.environ["WEAVIATE_API_KEY"])
        )

        chunks = retrieve(client, bedrock, question)
        answer, sources = generate(bedrock, question, chunks)

        trace.update(output={"answer": answer, "sources": sources})

        return {
            "statusCode": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"answer": answer, "sources": sources})
        }

    except Exception as e:
        print(f"ERROR: {e}")
        trace.update(output={"error": str(e)})
        return {
            "statusCode": 500,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        }

    finally:
        if client:
            client.close()
        langfuse.flush()