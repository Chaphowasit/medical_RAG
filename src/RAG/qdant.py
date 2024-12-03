from adaptors.qdrant_adaptors import QdrantAdaptor

if __name__ == "__main__":
    rag_adaptor = QdrantAdaptor()
    rag_adaptor.get_or_create_collection("medical")
    results = rag_adaptor.retrieval("คณะกรรมการ ค.ป.ท. มีความหมายว่าอะไร?")
    print(results)