import logging
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.models import Distance, PointStruct, VectorParams

from services.text_cleaner import TextCleaner
from services.thai_to_vec_embedder import Thai2VecEmbedder


class QdrantAdaptor:
    """
    A class to handle interactions with a Qdrant vector database.

    This class provides functionalities to process and store document embeddings,
    manage collections, and perform CRUD operations on data points in Qdrant.

    Attributes:
        collection_name (str): The name of the Qdrant collection.
        thai2vec (Thai2VecEmbedder): Embedding generator for text data.
        client (QdrantClient): Qdrant client for database interaction.
        text_cleaner (TextCleaner): Service for preprocessing text data.
        vector_size (int): The size of the vector embeddings.
    """

    def __init__(self, collection_name: str):
        """
        Initialize the QdrantAdaptor.

        Args:
            collection_name (str): The name of the Qdrant collection to use.
        """
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

    def create_collection(self, vector_size: int):
        """
        Creates a new collection in Qdrant.

        Args:
            vector_size (int): The size of the vector embeddings.
        """
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{self.collection_name}' created successfully.")

    def create_collection_if_not_exists(self, vector_size: int) -> bool:
        """
        Checks if a collection exists in Qdrant or creates it if not.

        Args:
            vector_size (int): The size of the vector embeddings.

        Returns:
            bool: True if the collection exists, False if it was newly created.
        """
        is_exists_collection = self.client.collection_exists(self.collection_name)
        if is_exists_collection:
            logging.info(f"Collection '{self.collection_name}' already exists.")
        else:
            self.create_collection(vector_size)

        logging.info(
            f"Vector store initialized for collection '{self.collection_name}'."
        )
        return is_exists_collection

    def add_documents_from_pdf(self, pdf_path: str, effective_date: str = None):
        """
        Adds documents from a PDF file to the vector store.

        Args:
            pdf_path (str): The file path of the PDF to process.
            effective_date (str, optional): The effective date to associate with the data.
                                             If not provided, the current datetime is used.
        """
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

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Successfully added {len(points)} chunk embeddings into Qdrant.")
        else:
            print("No valid chunk embeddings found.")

    def process_documents(self, process_chunks: list[Document]) -> list[PointStruct]:
        """
        Processes the documents and generates embeddings for each chunk.

        Args:
            process_chunks (list[Document]): A list of Document objects containing text and metadata.

        Returns:
            list[PointStruct]: A list of PointStruct objects ready to be inserted into Qdrant.
        """
        points = []
        for chunk in process_chunks:
            chunk_embedding = self.thai2vec.get_embedding(chunk.page_content)
            if chunk_embedding is not None:
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
        """
        Loads a PDF file, processes it, and adds its chunks to Qdrant as points.

        Args:
            file_path (str): The file path of the PDF to process.
            effective_date (str, optional): The effective date to associate with the data.
                                             Format: "YYYY-MM-DD HH:MM:SS.ffffff".
        """
        try:
            if not effective_date:
                effective_date_obj = datetime.now()
            else:
                effective_date_obj = datetime.strptime(
                    effective_date, "%Y-%m-%d %H:%M:%S.%f"
                )
        except ValueError:
            logging.error(
                "Invalid effective_date format. Use YYYY-MM-DD HH:MM:SS.ffffff"
            )
            effective_date_obj = datetime.now()

        existing_file_path = self.list_file_path()

        if file_path in existing_file_path:
            logging.warning(
                f"File '{file_path}' already exists in Qdrant metadata. No action taken."
            )
            return

        self.add_documents_from_pdf(
            file_path, effective_date_obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        )
        logging.info(f"File '{file_path}' processed and added to Qdrant.")

    def delete_file(self, file_path: str):
        """
        Deletes corresponding points with the given file_path from Qdrant.

        Args:
            file_path (str): The file path to identify and delete data points from Qdrant.
        """
        try:
            count = self._count_point()

            if count == 0:
                logging.warning(f"No points found in Qdrant Collection.")
                return

            points_to_delete = self.client.scroll(
                collection_name=self.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=count,
            )

            point_ids_to_delete = [
                point.id
                for point in points_to_delete[0]
                if point.payload.get("metadata").get("source") == file_path
            ]

            if point_ids_to_delete:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids_to_delete,
                )
                logging.info(
                    f"Points with file_path '{file_path}' deleted from Qdrant."
                )
            else:
                logging.warning(
                    f"No points found for file_path '{file_path}' in Qdrant."
                )
        except Exception as e:
            logging.error(f"Error deleting points with file_path '{file_path}': {e}")

    def list_file_path(self) -> list[str]:
        """
        Lists all file paths stored in Qdrant metadata.

        Returns:
            list[str]: A list of file paths present in Qdrant metadata.
        """
        try:
            count = self._count_point()

            if count == 0:
                logging.warning(f"No points found in Qdrant Collection.")
                return []

            points = self.client.scroll(
                collection_name=self.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=count,
            )
            file_path = set(
                [point.payload.get("metadata").get("source") for point in points[0]]
            )
            logging.info(f"file_path in Qdrant metadata: {file_path}")
            return list(file_path)
        except Exception as e:
            logging.error(f"Error retrieving file_path from Qdrant metadata: {e}")
            return []

    def _count_point(self) -> int:
        """
        Counts all points stored in the Qdrant collection.

        Returns:
            int: The number of points in the collection.
        """
        count = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        ).count

        return count
