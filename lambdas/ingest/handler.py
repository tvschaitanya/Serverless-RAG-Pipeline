import os
import json
import boto3
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Property, DataType
from firecrawl import FirecrawlApp

COLLECTION_NAME = os.environ["COLLECTION_NAME"]

def get_bedrock():
    return boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION_NAME"])

def chunk_text(text, chunk_size=150, overlap=15):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks

def embed(bedrock, text):
    response = bedrock.invoke_model(
        modelId="cohere.embed-english-v3",
        body=json.dumps({
            "texts": [text],
            "input_type": "search_document"
        })
    )
    return json.loads(response["body"].read())["embeddings"][0]

def reset_collection(client):
    if client.collections.exists(COLLECTION_NAME):
        client.collections.delete(COLLECTION_NAME)
    client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=None,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
        ]
    )
    return client.collections.get(COLLECTION_NAME)

def lambda_handler(event, context):
    firecrawl = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])
    bedrock = get_bedrock()
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.environ["WEAVIATE_URL"],
        auth_credentials=Auth.api_key(os.environ["WEAVIATE_API_KEY"])
    )

    try:
        url = os.environ["TARGET_URL"]
        print(f"Crawling: {url}")

        result = firecrawl.crawl_url(url, limit=int(os.environ.get("CRAWL_LIMIT", "10")))
        pages = result.data if hasattr(result, "data") else []
        print(f"Pages crawled: {len(pages)}")

        collection = reset_collection(client)
        total_chunks = 0
        failed_pages = 0

        with collection.batch.dynamic() as batch:
            for page in pages:
                try:
                    markdown = page.markdown if hasattr(page, "markdown") else ""
                    source = page.metadata.source_url if hasattr(page, "metadata") else ""
                    if not markdown:
                        continue

                    for chunk in chunk_text(markdown):
                        vector = embed(bedrock, chunk)
                        batch.add_object(
                            properties={"text": chunk, "source": source},
                            vector=vector
                        )
                        total_chunks += 1

                except Exception as e:
                    failed_pages += 1
                    print(f"ERROR on page {getattr(page.metadata, 'source_url', 'unknown')}: {e}")

        print(f"Done. Chunks: {total_chunks}, Failed pages: {failed_pages}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "chunks_stored": total_chunks,
                "pages_crawled": len(pages),
                "failed_pages": failed_pages
            })
        }

    finally:
        client.close()