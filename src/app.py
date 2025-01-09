import json
import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from adaptors.qdrant_adaptors import QdrantAdaptor
from services.chatbot import Chatbot
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Create a FastAPI instance
app = FastAPI()
load_dotenv(override=True)
collection_name = os.getenv("COLLECTION_NAME")

qdrant_adaptor = QdrantAdaptor(collection_name)
qrant_client = qdrant_adaptor.client
chatbot = Chatbot(qrant_client, collection_name)

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

# Mount the Vite build directory to serve static files
app.mount("/static", StaticFiles(directory="dist", html=True), name="static")

class ConnectionManager:
    """
    Class for managing WebSocket connections.

    This class handles connecting, disconnecting, and sending messages to WebSocket clients.
    """

    def __init__(self):
        """
        Initialize the ConnectionManager with an empty list of active connections.

        Attributes:
            active_connections (list): List of active WebSocket connections.
        """
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        """
        Accept a new WebSocket connection and add it to the active connections list.

        Args:
            websocket (WebSocket): The WebSocket connection to be accepted.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from the active connections list.

        Args:
            websocket (WebSocket): The WebSocket connection to be removed.
        """
        self.active_connections.remove(websocket)
        print(f"Connection closed. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a personal message to a specific WebSocket connection.

        Args:
            message (str): The message to send.
            websocket (WebSocket): The WebSocket connection to send the message to.
        """
        await websocket.send_json(message)


# Create a ConnectionManager instance to manage WebSocket connections
manager = ConnectionManager()


@app.websocket("/api/chatbot")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handle WebSocket connections for the chatbot.

    Args:
        websocket (WebSocket): The WebSocket connection to handle.
    """
    await manager.connect(websocket)
    try:
        while True:
            user_message = await websocket.receive_text()
            print(f"Received message: {user_message}")
            async for response, source, filename in chatbot.stream_response(
                user_message
            ):
                result = {"response": response, "source": source, "filename": filename}
                await manager.send_personal_message(result, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        manager.disconnect(websocket)


@app.post("/files/create")
async def create_file(file: UploadFile = File(...)):
    """
    API endpoint to upload a file and add its content to the Qdrant collection.

    Args:
        file (UploadFile): The file to be uploaded and processed.

    Returns:
        dict: A success message indicating the file has been added to the collection.

    Raises:
        HTTPException: If there is an error while creating the file.
    """
    try:
        data_dir = "./data/"
        os.makedirs(data_dir, exist_ok=True)

        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        qdrant_adaptor.create_file(file_path)

        return {"message": f"File '{file.filename}' added to collection."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating file: {e}")


@app.get("/files/list")
async def list_files():
    """
    API endpoint to list all files in the Qdrant collection.

    Returns:
        dict: A list of filenames present in the collection.

    Raises:
        HTTPException: If there is an error while listing files.
    """
    try:
        filenames = qdrant_adaptor.list_file_path()
        filenames = [os.path.basename(filename) for filename in filenames]
        return {"filenames": filenames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {e}")


@app.delete("/files/delete")
async def delete_file(filename: str):
    """
    API endpoint to delete a file from the Qdrant collection and local storage.

    Args:
        filename (str): The name of the file to be deleted.

    Returns:
        dict: A success message indicating the file has been deleted.

    Raises:
        HTTPException: If there is an error while deleting the file.
    """
    try:
        file_path = f"./data/{filename}"

        qdrant_adaptor.delete_file(file_path)

        filenames_after_deletion = qdrant_adaptor.list_file_path()
        if file_path in filenames_after_deletion:
            raise HTTPException(
                status_code=500,
                detail=f"File '{filename}' could not be deleted from the collection.",
            )

        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "message": f"File '{filename}' deleted from collection and local storage."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
