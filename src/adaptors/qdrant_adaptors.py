import logging
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.models import Distance, VectorParams
from langchain_text_splitters import RecursiveCharacterTextSplitter

from services.text_cleaner import TextCleaner
from services.thai_to_vec_embedder import Thai2VecEmbedder


class QdrantAdaptor:
    def __init__(self, collection_name):
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
        
        self.collection_name = collection_name
        self.vector_size = 300
        self.create_collection_if_not_exists(self.vector_size)

    def create_collection(self, vector_size):
        """Creates a new collection in Qdrant."""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{self.collection_name}' created successfully.")

    def create_collection_if_not_exists(self, vector_size):
        """Checks if a collection exists or creates it if not."""
        is_exists_collection = self.client.collection_exists(self.collection_name)
        if is_exists_collection:
            logging.info(f"Collection '{self.collection_name}' already exists.")
        else:
            self.create_collection(vector_size)

        logging.info(f"Vector store initialized for collection '{self.collection_name}'.")
        return is_exists_collection

    # Recursive Character Text Splitter
    def add_documents_from_pdf(self, pdf_path: str, effective_date: str = None):
        """Adds documents from a PDF file to the vector store."""
        if not effective_date:
            effective_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

        chunks = text_splitter.split_documents(documents)
        process_chunks = []
        for c in chunks:
            c.page_content = self.text_cleaner.preprocess_text(c.page_content)
            metadata_with_date = c.metadata.copy()
            metadata_with_date["effective_date"] = effective_date
            process_chunks.append(
                Document(page_content=c.page_content, metadata=metadata_with_date)
            )

        points = self.process_documents(process_chunks)
        
        # Insert chunk embeddings into Qdrant
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Successfully added {len(points)} chunk embeddings into Qdrant.")
        else:
            print("No valid chunk embeddings found.")

    def process_documents(self, process_chunks):
        points = []

        for chunk in process_chunks:
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

    def create_file(self, file_path: str, effective_date: str = None):
        """Loads a PDF file, processes it, and adds its chunks to Qdrant as points."""
        try:
            if not effective_date:
                effective_date_obj = datetime.now()
            else:
                effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            logging.error("Invalid effective_date format. Use YYYY-MM-DD HH:MM:SS.ffffff")
        finally:
            effective_date_obj = datetime.now()

        # Retrieve existing file_path using list_file_path
        existing_file_path = self.list_file_path()

        if file_path in existing_file_path:
            logging.warning(f"File '{file_path}' already exists in Qdrant metadata. No action taken.")
            return

        # Process and add PDF content to Qdrant
        self.add_documents_from_pdf(file_path, effective_date_obj.strftime("%Y-%m-%d %H:%M:%S.%f"))
        logging.info(f"File '{file_path}' processed and added to Qdrant.")



    def delete_file(self, file_path: str):
        """Deletes corresponding points with the given file_path from Qdrant."""
        try:
            # Use filtering to find points with the specified file_path
            count = self._count_point()
            
            if count == 0:
                logging.warning(f"No points found in Qdrant Collection.")
                return
            
            points_to_delete = self.client.scroll(
                collection_name=self.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=count
            )
            
            point_ids_to_delete = [point.id for point in points_to_delete[0] if point.payload.get("metadata").get("source") == file_path]

            if point_ids_to_delete :
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids_to_delete
                )
                logging.info(f"Points with file_path '{file_path}' deleted from Qdrant.")
            else:
                logging.warning(f"No points found for file_path '{file_path}' in Qdrant.")
                return
            
        except Exception as e:
            logging.error(f"Error deleting points with file_path '{file_path}': {e}")

    def list_file_path(self):
        """Lists all file_path stored in Qdrant metadata."""
        try:
            count = self._count_point()
            
            if count == 0:
                logging.warning(f"No points found in Qdrant Collection.")
                return
            
            points = self.client.scroll(
                collection_name=self.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=count
            )
            file_path = set([point.payload.get("metadata").get("source") for point in points[0]])
            logging.info(f"file_path in Qdrant metadata: {file_path}")
            return file_path
        except Exception as e:
            logging.error(f"Error retrieving file_path from Qdrant metadata: {e}")
            return []
        
    def _count_point(self):
        """Count all point stored in Qdrant Collection"""
        count = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        ).count
        
        return count
