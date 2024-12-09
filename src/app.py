from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from adaptors.qdrant_adaptors import QdrantAdaptor

app = FastAPI()

# Initialize QdrantAdaptor
adaptor = QdrantAdaptor()
adaptor.get_or_create_collection(collection_name="medical")


# Define a model for the incoming JSON request
class QueryRequest(BaseModel):
    user_query: str


@app.post("/", response_class=JSONResponse)
def submit(request: QueryRequest):
    user_query = request.user_query
    results = adaptor.retrieval(query=user_query, top_k=6)
    return {"user_query": user_query, "results": results}
