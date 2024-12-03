import logging
import os

from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv

class QdrantAdaptor:
    def __init__(self):
        load_dotenv(override=True)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002", 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )

    def create_collection(self, collection_name: str, vector_size: int = 1536):
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{collection_name}' created successfully.")
    
    def get_or_create_collection(self, collection_name: str, vector_size: int = 1536):
        
        if self.client.collection_exists(collection_name):
            logging.info(f"Collection '{collection_name}' already exists.")
        else:
            self.create_collection(collection_name, vector_size)

        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self.embeddings,
        )
    
    def retrieval(self, query: str, top_k: int = 2):
        similarity_response = self.vector_store.similarity_search(query=query, k=top_k)
        results = dict()
        for rank, result in enumerate(similarity_response):
            results[rank] = {"Content": result.page_content, "Metadata" : result.metadata}
        return results