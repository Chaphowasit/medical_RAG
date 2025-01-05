import sys
import os

# Adding the adaptor module to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adaptors.qdrant_adaptors import QdrantAdaptor
from datetime import datetime

if __name__ == "__main__":
    # Define the collection name and PDF path
    collection_name = "medical1"
    pdf_path = "src\\data\\sample.pdf"
    
    # Initialize the Qdrant adaptor
    adaptor = QdrantAdaptor(collection_name)

    # Step 1: Use create_file function to add documents
    print("Creating collection and adding documents using create_file...")
    adaptor.create_file(pdf_path)
    print(f"Documents from '{pdf_path}' added to collection '{collection_name}' using create_file.")

    # Step 2: List all filenames in the collection
    print("Listing filenames in the collection...")
    filenames = adaptor.list_file_path()
    print(f"Filenames in the collection: {filenames}")

    # Step 3: Delete a specific file from the collection
    filename_to_delete = pdf_path
    print(f"Deleting filename '{filename_to_delete}' from the collection...")
    adaptor.delete_file(filename_to_delete)
    print(f"Filename '{filename_to_delete}' deleted from the collection.")

    # Verify the deletion
    print("Verifying deletion...")
    filenames_after_deletion = adaptor.list_file_path()
    print(f"Filenames after deletion: {filenames_after_deletion}")
