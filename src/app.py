from fastapi import FastAPI, WebSocket
from adaptors.qdrant_adaptors import QdrantAdaptor
from services.chatbot import Chatbot
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Create a FastAPI instance
app = FastAPI()
qdrant_adaptor = QdrantAdaptor("medical")
qrant_client = qdrant_adaptor.client
chatbot = Chatbot(qrant_client)

# Add CORS middleware to allow cross-origin requests
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define the WebSocket endpoint for chatbot connections
class ConnectionManager:
    """Class defining socket events for managing WebSocket connections."""

    def __init__(self):
        """Initialize the manager with an empty list of active connections."""
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        """Handle a new connection and accept the WebSocket.
        Args:
            websocket (WebSocket): The WebSocket connection to accept.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Handle a disconnection by removing the WebSocket from the list.
        Args:
            websocket (WebSocket): The WebSocket connection to disconnect.
        """
        self.active_connections.remove(websocket)
        print(f"Connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a personal message to a specific WebSocket connection.
        Args:
            message (str): The message to send.
            websocket (WebSocket): The WebSocket connection to send the message to.
        """
        await websocket.send_text(message)


# Create a ConnectionManager instance to manage WebSocket connections
manager = ConnectionManager()


# Define the WebSocket endpoint for chatbot connections
@app.websocket("/chatbot")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections at this endpoint."""
    await manager.connect(websocket)
    try:
        while True:
            user_message = await websocket.receive_text()
            print(f"Received message: {user_message}")
            async for response in chatbot.stream_response(user_message):
                await manager.send_personal_message(response, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket)
