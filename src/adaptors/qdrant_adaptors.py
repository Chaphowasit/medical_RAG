import logging
import os
import re
import unicodedata
from typing import List
import tiktoken
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_openai import OpenAI
from langchain_experimental.text_splitter import SemanticChunker


class NLPTransformation:
    def __init__(self):
        """Initialize the NLPTransformation"""
        self.tokenizer = tiktoken.get_encoding("o200k_base")

    @staticmethod
    def thai_to_arabic(text: str) -> str:
        """Converts Thai numerals in a string to Arabic numerals."""
        thai_to_arabic_map = str.maketrans("๑๒๓๔๕๖๗๘๙๐", "1234567890")
        return text.translate(thai_to_arabic_map)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Applies text normalization: Unicode normalization and lowercase conversion."""
        text = unicodedata.normalize("NFC", text)
        return text.lower()

    @staticmethod
    def remove_unimportant_word(text: str) -> str:
        """Removes extra spaces and normalizes the text, removing single Thai characters inside parentheses."""
        text = re.sub(r"[\n\r\t]+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\([a-zA-Zก-ฮ]\)", "", text)
        text = re.sub(
            r"([\u0E01-\u0E2E])\s+([\u0E30-\u0E39\u0E47-\u0E4F])", r"\1\2", text
        )
        return text

    def preprocess_text(self, text: str) -> str:
        """Preprocess Thai text (e.g., normalization, segmentation)."""
        text = self.thai_to_arabic(text)
        # text = self.normalize_text(text)
        text = self.remove_unimportant_word(text)
        return text

    # def split_text_into_chunks(
    #     self, text: str, max_tokens: int = 80, overlap_tokens: int = 60
    # ) -> List[str]:
    #     """Splits text into chunks based on token count with overlap."""
    #     tokens = self.tokenizer.encode(text)
    #     chunks = []
    #     start_idx = 0
    #     while start_idx < len(tokens):
    #         end_idx = start_idx + max_tokens
    #         chunk_tokens = tokens[start_idx:end_idx]
    #         chunk = self.tokenizer.decode(chunk_tokens)
    #         chunks.append(chunk)
    #         start_idx = end_idx - overlap_tokens
    #     return chunks


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

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large", api_key=openai_api_key
        )
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.vector_store = None
        self.nlp_adaptor = NLPTransformation()
        self.chunk_size = 400
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=100,
            add_start_index=True,
        )
        self.semantic_chunker = SemanticChunker(
            self.embeddings, breakpoint_threshold_type="standard_deviation"
        )

    def create_collection(self, collection_name: str, vector_size: int = 3072):
        """Creates a new collection in Qdrant."""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logging.info(f"Collection '{collection_name}' created successfully.")

    def get_or_create_collection(self, collection_name: str, vector_size: int = 3072):
        """Checks if a collection exists or creates it if not."""
        get_or_create = self.client.collection_exists(collection_name)
        if get_or_create:
            logging.info(f"Collection '{collection_name}' already exists.")
        else:
            self.create_collection(collection_name, vector_size)

        self.vector_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection_name,
            embedding=self.embeddings,
        )
        logging.info(f"Vector store initialized for collection '{collection_name}'.")
        return not get_or_create

    # def clean_and_chunk_text(self, text: str) -> List[dict]:
    #     """Cleans and processes text into chunks with overlap, extracting keywords."""
    #     text = self.nlp_adaptor.preprocess_text(text)
    #     chunks = self.nlp_adaptor.split_text_into_chunks(text)
    #     processed_chunks = []

    #     for chunk in chunks:
    #         keywords = self.nlp_adaptor.extract_keywords(chunk)
    #         processed_chunks.append({"content": chunk, "keywords": keywords})

    #     return processed_chunks

    # def check_splitter(self, text: str, length_previous: int, current_page: int):
    #     chunks_list = self.text_splitter(text)
    #     chunk_sources = list()
    #     for chunk in chunks_list:
    #         start_index = text.find(chunk)
    #         end_index = start_index + len(chunk) - 1
    #         if start_index <= length_previous and end_index <= length_previous:
    #             chunk_sources.append(f"Page {current_page-1}")
    #         elif (
    #             start_index >= length_previous + 1 and end_index >= length_previous + 1
    #         ):
    #             chunk_sources.append(f"Page {current_page}")
    #         else:
    #             chunk_sources.append(f"Page {current_page-1}, {current_page}")
    #     return chunks_list, chunk_sources

    # def processing_chunk(self, chunks_list: list):
    #     processed_chunks = list()
    #     for chunk in chunks_list:
    #         keywords = self.nlp_adaptor.extract_keywords(chunk)
    #         processed_chunks.append({"content": chunk, "keywords": keywords})
    #     return processed_chunks

    # def add_documents_from_pdf_copy(self, pdf_path: str):
    #     """Loads documents from a PDF, processes them, and inserts them into the collection."""
    #     if not self.vector_store:
    #         raise ValueError(
    #             "Vector store is not initialized. Call `get_or_create_collection` first."
    #         )
    #     logging.info(f"Processing PDF '{pdf_path}'...")
    #     loader = PyPDFLoader(pdf_path)
    #     documents = loader.load()
    #     processed_chunks = []
    #     last_file_index = len(documents)
    #     processed_chunks = self.text_splitter.split_documents(documents)
    #     # for index in range(1, last_file_index):
    #     # for doc in documents:

    #     # documents_previous = documents[index - 1].page_content
    #     # documents_current = documents[index].page_content

    #     # length_documents_previous = len(documents_previous)
    #     # length_documents_current = len(documents_current)

    #     # full_text_documents = documents_previous + "\n" + documents_current

    #     # clean_text = self.nlp_adaptor.preprocess_text(full_text_documents)
    #     # processed_chunks += [self.text_splitter.split_documents(doc)]
    #     # processed_chunks += [self.text_splitter.split_documents([doc])]
    #     # chunks_list, chunk_sources = self.check_splitter(
    #     #     clean_text,
    #     #     length_documents_previous,
    #     #     length_documents_current.metadata["page"],
    #     # )

    #     # if index != last_file_index:
    #     #     chunks_list.pop()
    #     #     chunk_sources.pop()

    #     # processed_chunks = self.processing_chunk(chunks_list)

    #     # for chunk_data, source in zip(processed_chunks, chunk_sources):
    #     #     chunk_content = chunk_data["content"]
    #     #     keywords = chunk_data["keywords"]

    #     # for doc in documents:
    #     #     cleaned_chunks = self.clean_and_chunk_text(doc.page_content)
    #     #     for chunk_data in cleaned_chunks:
    #     #         chunk_content = chunk_data["content"]
    #     #         keywords = chunk_data["keywords"]

    #     #         existing_metadata = doc.metadata if doc.metadata else {}
    #     #         updated_metadata = {**existing_metadata, "keywords": keywords}

    #     #         doc_copy = doc.model_copy(
    #     #             update={
    #     #                 "page_content": chunk_content,
    #     #                 "metadata": updated_metadata,
    #     #             }
    #     #         )
    #     #         processed_chunks.append(doc_copy)

    #     self.vector_store.add_documents(documents=processed_chunks)
    #     logging.info(
    #         f"Added {len(processed_chunks)} chunks from '{pdf_path}' to the vector store with keywords."
    #     )

    # Contextual Retrieval
    # def add_documents_from_pdf(self, pdf_path: str):
    #     """Loads documents from a PDF, applies contextual enrichment in Thai, and inserts them into the collection."""
    #     if not self.vector_store:
    #         raise ValueError(
    #             "Vector store is not initialized. Call `get_or_create_collection` first."
    #         )

    #     logging.info(f"Processing PDF '{pdf_path}'...")

    #     # Step 1: Load the PDF and split into chunks
    #     loader = PyPDFLoader(pdf_path)
    #     documents = loader.load()
    #     chunks = self.text_splitter.split_documents(documents)

    #     # Step 2: Combine all document content to provide global context
    #     global_context = "\n".join([doc.page_content for doc in documents])

    #     # Step 3: Enrich each chunk with global context using OpenAI, in Thai language
    #     llm = OpenAI(
    #         temperature=0.3,  # Lower temperature for more focused responses
    #         api_key=os.getenv("OPENAI_API_KEY"),
    #     )
    #     enriched_chunks = []

    #     for chunk in chunks:
    #         try:
    #             enriched_content = llm(
    #                 f""" "ถังข้อมูล: {chunk.page_content}\n\n"
    #                 "ช่วยสรุปบริบทของข้อมูลนี้จากข้อมูลทั้งหมดให้หน่อยว่าเกี่ยวข้องกับอะไร โดยขึ้นต้นประโยคว่า "ข้อมูลนี้เกี่ยวข้องกับ" โดยใช้คำศัพท์ที่เหมาะสมและสั้นๆกระชับ"""
    #             )

    #             # Improve the enriched context with clearer instructions
    #             updated_metadata = chunk.metadata.copy()  # Copy existing metadata
    #             updated_metadata["context"] = (
    #                 enriched_content.strip()
    #             )  # Add the new "context" key

    #             # Store the original chunk content in page_content and the updated metadata
    #             enriched_chunks.append(
    #                 Document(
    #                     page_content=chunk.page_content,  # Keep the original content
    #                     metadata=updated_metadata,  # Use updated metadata with added context
    #                 )
    #             )
    #         except Exception as e:
    #             logging.error(f"Error during enrichment for chunk: {e}")
    #             enriched_chunks.append(
    #                 Document(
    #                     page_content=chunk.page_content,  # Keep original content if enrichment fails
    #                     metadata=chunk.metadata,  # Keep original metadata if enrichment fails
    #                 )
    #             )

    #     # Step 4: Embed enriched chunks into the vector store
    #     self.vector_store.add_documents(enriched_chunks)

    #     logging.info(
    #         f"Added {len(enriched_chunks)} enriched chunks from '{pdf_path}' to the vector store."
    #     )

    # Contextual Retrieval Tiger
    # def add_documents_from_pdf(self, pdf_path: str):
    #     """Loads documents from a PDF, applies contextual enrichment in Thai, and inserts them into the collection."""
    #     if not self.vector_store:
    #         raise ValueError(
    #             "Vector store is not initialized. Call `get_or_create_collection` first."
    #         )

    #     logging.info(f"Processing PDF '{pdf_path}'...")

    #     # Step 1: Load the PDF and split into chunks
    #     loader = PyPDFLoader(pdf_path)
    #     documents = loader.load()
    #     chunks = self.text_splitter.split_documents(documents)

    #     # Step 2: Combine all document content to provide global context
    #     global_context = "\n".join([doc.page_content for doc in documents])

    #     # Step 3: Enrich each chunk with global context using OpenAI, in Thai language
    #     llm = OpenAI(
    #         temperature=0.3,  # Lower temperature for more focused responses
    #         api_key=os.getenv("OPENAI_API_KEY"),
    #     )
    #     enriched_chunks = []

    #     for chunk in chunks:
    #         try:
    #             enriched_content = llm(
    #                 f""" "ถังข้อมูล: {chunk.page_content}\n\n"
    #                 "ช่วยสรุปบริบทของข้อมูลนี้จากข้อมูลทั้งหมดให้หน่อยว่าเกี่ยวข้องกับอะไร โดยขึ้นต้นประโยคว่า "ข้อมูลนี้เกี่ยวข้องกับ" โดยใช้คำศัพท์ที่เหมาะสมและสั้นๆกระชับ"""
    #             )

    #             # Improve the enriched context with clearer instructions
    #             updated_metadata = chunk.metadata.copy()  # Copy existing metadata
    #             updated_metadata["context"] = (
    #                 enriched_content.strip()
    #             )  # Add the new "context" key

    #             # Store the original chunk content in page_content and the updated metadata
    #             enriched_chunks.append(
    #                 Document(
    #                     page_content=chunk.page_content,  # Keep the original content
    #                     metadata=updated_metadata,  # Use updated metadata with added context
    #                 )
    #             )
    #         except Exception as e:
    #             logging.error(f"Error during enrichment for chunk: {e}")
    #             enriched_chunks.append(
    #                 Document(
    #                     page_content=chunk.page_content,  # Keep original content if enrichment fails
    #                     metadata=chunk.metadata,  # Keep original metadata if enrichment fails
    #                 )
    #             )

    #     # Step 4: Embed enriched chunks into the vector store
    #     self.vector_store.add_documents(enriched_chunks)

    #     logging.info(
    #         f"Added {len(enriched_chunks)} enriched chunks from '{pdf_path}' to the vector store."
    #     )

    # Semantic Chunking
    def add_documents_from_pdf(self, pdf_path: str):
        """Loads documents from a PDF, applies contextual enrichment in Thai, and inserts them into the collection."""
        if not self.vector_store:
            raise ValueError(
                "Vector store is not initialized. Call `get_or_create_collection` first."
            )

        logging.info(f"Processing PDF '{pdf_path}'...")

        # Step 1: Load the PDF and split into chunks
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        semantic_chunks = self.semantic_chunker.create_documents(
            [self.nlp_adaptor.preprocess_text(d.page_content) for d in documents],
            [d.metadata for d in documents],
        )

        # for semantic_chunk in semantic_chunks:
        #     if "Effect of Pre-training Tasks" in semantic_chunk.page_content:
        #         print(semantic_chunk.page_content)
        #         print(len(semantic_chunk.page_content))

        self.vector_store.add_documents(semantic_chunks)

        logging.info(
            f"Added {len(semantic_chunks)} enriched chunks from '{pdf_path}' to the vector store."
        )
