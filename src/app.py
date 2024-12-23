from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.chatbot import Chatbot
from adaptors.qdrant_adaptors import QdrantAdaptor

app = FastAPI()
qdrant_adaptor = QdrantAdaptor()
qrant_client = qdrant_adaptor.client
chatbot = Chatbot(qrant_client)


class QueryRequest(BaseModel):
    user_query: str

@app.get("/", response_class=JSONResponse)
def health_check():
    try:
        if not qrant_client:
            return JSONResponse(status_code=500, content={"status": "unhealthy"})
        return {"status": "healthy"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "unhealthy", "error": str(e)})
    
@app.post("/chatbot", response_class=JSONResponse)
def submit(request: QueryRequest):
    user_query = request.user_query
    response_message, reference_content = chatbot.response(user_query)
    return {"user_query": user_query, "result": {"response_message": response_message, "reference_content": reference_content}}