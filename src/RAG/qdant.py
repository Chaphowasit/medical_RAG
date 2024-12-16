import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adaptors.qdrant_adaptors import QdrantAdaptor

if __name__ == "__main__":
    adaptor = QdrantAdaptor()
    collection_name = "medical"
    pdf_path = "src\\data\\sample.pdf"

    is_exists_collection = adaptor.get_or_create_collection(collection_name)
    if not is_exists_collection:
        adaptor.add_documents_from_pdf(pdf_path)