import logging
import os
import uuid
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.models import Distance, VectorParams
from langchain_text_splitters import RecursiveCharacterTextSplitter

from pythainlp import word_vector

from services.text_cleaner import TextCleaner
from services.thai_to_vec_embedder import Thai2VecEmbedder


class QdrantAdaptor:
    def __init__(self):
        """Initialize the QdrantAdaptor, load environment variables, and configure logging."""
        load_dotenv(override=True)
        logging.basicConfig(level=logging.INFO)

        openai_api_key = os.getenv("OPENAI_API_KEY")
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not openai_api_key or not qdrant_url or not qdrant_api_key:
            raise ValueError(
                "Missing required API keys or URLs in environment variables."
            )

        self.thai2vec = Thai2VecEmbedder()
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.text_cleaner = TextCleaner()

    def create_collection(self, collection_name: str, vector_size: int = 300):
        """Creates a new collection in Qdrant."""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{collection_name}' created successfully.")

    def get_or_create_collection(self, collection_name: str, vector_size: int = 300):
        """Checks if a collection exists or creates it if not."""
        get_or_create = self.client.collection_exists(collection_name)
        if get_or_create:
            logging.info(f"Collection '{collection_name}' already exists.")
        else:
            self.create_collection(collection_name, vector_size)

        logging.info(f"Vector store initialized for collection '{collection_name}'.")
        return not get_or_create

    # Recursive Character Text Splitter
    def add_documents_from_pdf(self, pdf_path: str):
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

        chunks = text_splitter.split_documents(documents)
        process_chunks = []
        for c in chunks:
            c.page_content = self.text_cleaner.preprocess_text(c.page_content)
            process_chunks.append(
                Document(page_content=c.page_content, metadata=c.metadata)
            )

        points = self.process_documents(process_chunks)

        # Insert chunk embeddings into Qdrant
        if points:
            self.client.upsert(collection_name="medical", points=points)
            print(f"Successfully added {len(points)} chunk embeddings into Qdrant.")
        else:
            print("No valid chunk embeddings found.")

    def process_documents(self, process_chunks):
        points = []

        for idx, chunk in enumerate(process_chunks):
            # Tokenize and generate embeddings for each chunk
            chunk_embedding = self.thai2vec.get_embedding(chunk.page_content)

            if chunk_embedding is not None:
                # Create a PointStruct for Qdrant
                points.append(
                    PointStruct(
                        id=uuid.uuid4().hex,
                        vector=chunk_embedding.tolist(),
                        payload={
                            "page_content": chunk.page_content,
                            "metadata": chunk.metadata,
                        },
                    )
                )

        return points
