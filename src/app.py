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


@app.post("/chatbot", response_class=JSONResponse)
def submit(request: QueryRequest):
    user_query = request.user_query
    result = chatbot.response(user_query)
    return {"user_query": user_query, "result": result}
