import json
import os
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket
from adaptors.qdrant_adaptors import QdrantAdaptor
from services.chatbot import Chatbot
from starlette.websockets import WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Create a FastAPI instance
app = FastAPI()
qdrant_adaptor = QdrantAdaptor("law")
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
        await websocket.send_json(message)


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
            async for response, source, filename in chatbot.stream_response(
                user_message
            ):
                result = {"response": response, "source": source, "filename": filename}
                # print(result)
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
    API endpoint to upload and create a file in the collection.

    Args:
        file (UploadFile): The file to be uploaded and added.

    Returns:
        dict: Success message if the file is added successfully.
    """
    try:
        # Define the directory to store files
        data_dir = ".\\data\\"
        os.makedirs(data_dir, exist_ok=True)

        # Save the uploaded file to the data directory
        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Use the adaptor to add the file to the collection
        qdrant_adaptor.create_file(file_path)

        return {"message": f"File '{file.filename}' added to collection."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating file: {e}")


@app.get("/files/list")
async def list_files():
    """
    API endpoint to list all files in the collection.

    Returns:
        dict: List of filenames in the collection.
    """
    try:
        filenames = qdrant_adaptor.list_file_path()
        # Extract only the filenames from paths
        filenames = [os.path.basename(filename) for filename in filenames]
        return {"filenames": filenames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {e}")


@app.delete("/files/delete")
async def delete_file(filename: str):
    """
    API endpoint to delete a file from the collection and remove it from local storage.

    Args:
        filename (str): Name of the file to be deleted.

    Returns:
        dict: Success message if the file is deleted successfully.
    """
    try:
        # Construct the full path
        file_path = f".\\data\\{filename}"

        # Delete file from the collection
        qdrant_adaptor.delete_file(file_path)

        # Check if file still exists in the collection
        filenames_after_deletion = qdrant_adaptor.list_file_path()
        if file_path in filenames_after_deletion:
            raise HTTPException(
                status_code=500,
                detail=f"File '{filename}' could not be deleted from the collection.",
            )

        # Remove the file from local storage
        if os.path.exists(file_path):
            os.remove(file_path)

        return {
            "message": f"File '{filename}' deleted from collection and local storage."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {e}")
