# from fastapi import FastAPI
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from services.chatbot import Chatbot
# from adaptors.qdrant_adaptors import QdrantAdaptor

# app = FastAPI()

# origins = [
#     "*",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# qdrant_adaptor = QdrantAdaptor()
# qrant_client = qdrant_adaptor.client
# chatbot = Chatbot(qrant_client)


# class QueryRequest(BaseModel):
#     user_query: str


# @app.get("/", response_class=JSONResponse)
# def health_check():
#     try:
#         if not qrant_client:
#             return JSONResponse(status_code=500, content={"status": "unhealthy"})
#         return {"status": "healthy"}
#     except Exception as e:
#         return JSONResponse(
#             status_code=500, content={"status": "unhealthy", "error": str(e)}
#         )


# @app.post("/chatbot", response_class=JSONResponse)
# def submit(request: QueryRequest):
#     user_query = request.user_query
#     response_message, reference_content = chatbot.response(user_query)
#     return {
#         "user_query": user_query,
#         "result": {
#             "response_message": response_message,
#             "reference_content": reference_content,
#         },
#     }

from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketState
from adaptors.qdrant_adaptors import QdrantAdaptor
from services.chatbot import Chatbot
from starlette.websockets import WebSocketDisconnect

app = FastAPI()
qdrant_adaptor = QdrantAdaptor("medical")
qrant_client = qdrant_adaptor.client
chatbot = Chatbot(qrant_client)


@app.websocket("/chatbot")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            user_message = await websocket.receive_text()
            async for response in chatbot.stream_response(user_message):
                await websocket.send_text(response)
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception as e:
            print(f"Error during WebSocket close: {e}")
