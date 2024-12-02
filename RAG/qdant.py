from langchain_community.document_loaders import PyPDFLoader
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os
from dotenv import load_dotenv

load_dotenv()

embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002", api_key=os.getenv("OPENAI_API_KEY")
)
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)


# 1. Create a Collection
def create_collection(collection_name: str, vector_size: int = 1536):
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    print(f"Collection '{collection_name}' created successfully.")


# 2. Get All Collections
def get_all_collections():
    collections = client.get_collections().collections
    return [collection.name for collection in collections]


# 3. Delete a Collection
def delete_collection(collection_name: str):
    client.delete_collection(collection_name=collection_name)
    print(f"Collection '{collection_name}' deleted successfully.")


# 4. RAG with OpenAI Embed and PDF
def rag_with_pdf(pdf_path: str, collection_name: str, query: str, top_k: int = 1):
    # Load PDF using PyPDFLoader
    # loader = PyPDFLoader(pdf_path)
    # documents = loader.load()

    # Prepare vector store
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    # vector_store = QdrantVectorStore.from_existing_collection(
    #     embedding=embeddings,
    #     collection_name=collection_name,
    #     url=os.getenv("QDRANT_URL"),
    # )

    # Add documents to the vector store
    # vector_store.add_documents(documents=documents)

    # Query the vector store
    results = vector_store.similarity_search(query=query, k=top_k)
    return results


# Usage Examples
# 1. Create a new collection
# create_collection("medical")

# 2. List all collections
print("Collections:", get_all_collections())

# 3. Delete a collection
# delete_collection("medical")

# 4. RAG with PDF
pdf_path = "./data/sample.pdf"  # Replace with your PDF path
query = "คณะกรรมการ ค.ป.ท. มีความหมายว่าอะไร?"
results = rag_with_pdf(pdf_path, "medical", query)

# Display results
for result in results:
    print(f"Content: {result.page_content}")
    print(f"Metadata: {result.metadata}")
