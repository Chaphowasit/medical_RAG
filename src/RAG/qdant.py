import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adaptors.qdrant_adaptors import QdrantAdaptor

if __name__ == "__main__":
    adaptor = QdrantAdaptor()
    collection_name = "medical"
    pdf_path = "src\\data\\sample.pdf"
    query = "มาตรา 1"

    is_new_collection = adaptor.get_or_create_collection(collection_name)
    if is_new_collection:
        adaptor.add_documents_from_pdf(pdf_path)

    # results = adaptor.retrieval(query=query, top_k=10)

    # for rank, result in results.items():
    #     print(f"Rank {rank + 1}:")
    #     print(f"Content: {result['Content']}")
    #     print(f"Metadata: {result['Metadata']}")
