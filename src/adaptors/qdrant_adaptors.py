import logging
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams


class QdrantAdaptor:
    def __init__(self):
        load_dotenv(override=True)
        logging.basicConfig(level=logging.INFO)
        print(os.getenv("OPENAI_API_KEY"))  # Debug print to confirm environment loading
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002", api_key=os.getenv("OPENAI_API_KEY")
        )
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.vector_store = None

    def create_collection(self, collection_name: str, vector_size: int = 1536):
        """Creates a new collection in Qdrant."""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{collection_name}' created successfully.")

    def get_or_create_collection(self, collection_name: str, vector_size: int = 1536):
        """Checks if a collection exists or creates it if not."""
        collection_exists = self.client.collection_exists(collection_name)
        if collection_exists:
            logging.info(f"Collection '{collection_name}' already exists.")
        else:
            self.create_collection(collection_name, vector_size)
        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self.embeddings,
        )
        return not collection_exists  # Returns True if the collection did not exist

    @staticmethod
    def thai_to_arabic(text: str) -> str:
        """Converts Thai numerals in a string to Arabic numerals."""
        thai_to_arabic_map = str.maketrans("๑๒๓๔๕๖๗๘๙๐o", "12345678900")
        return text.translate(thai_to_arabic_map)

    def add_documents_from_pdf(self, pdf_path: str):
        """Loads documents from a PDF and inserts them into the collection."""
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        # Map Thai numbers to Arabic numbers in document content
        for doc in documents:
            doc.page_content = self.thai_to_arabic(doc.page_content)

        self.vector_store.add_documents(documents=documents)
        logging.info(
            f"Added {len(documents)} documents from '{pdf_path}' to the vector store."
        )

    def retrieval(self, query: str, top_k: int = 6):
        """Performs a similarity search."""
        similarity_response = self.vector_store.similarity_search(query=query, k=top_k)
        results = dict()
        for rank, result in enumerate(similarity_response):
            results[rank] = {
                "Content": result.page_content,
                "Metadata": result.metadata,
            }
        return results
