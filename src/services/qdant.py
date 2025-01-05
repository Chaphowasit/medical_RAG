import sys
import os
import logging
from adaptors.qdrant_adaptors import QdrantAdaptor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main(collection_name, pdf_path):
    adaptor = QdrantAdaptor(collection_name)

    try:
        logging.info("Creating collection and adding documents using create_file...")
        adaptor.create_file(pdf_path)
        logging.info(
            f"Documents from '{pdf_path}' added to collection '{collection_name}' using create_file."
        )
    except Exception as e:
        logging.error(f"Error during create_file: {e}")

    try:
        logging.info("Listing filenames in the collection...")
        filenames = adaptor.list_file_path()
        logging.info(f"Filenames in the collection: {filenames}")
        assert pdf_path in filenames, f"File '{pdf_path}' should be in the collection."
    except Exception as e:
        logging.error(f"Error during listing filenames: {e}")

    try:
        logging.info(f"Deleting filename '{pdf_path}' from the collection...")
        adaptor.delete_file(pdf_path)
        logging.info(f"Filename '{pdf_path}' deleted from the collection.")
    except Exception as e:
        logging.error(f"Error during delete_file: {e}")

    try:
        logging.info("Verifying deletion...")
        filenames_after_deletion = adaptor.list_file_path()
        logging.info(f"Filenames after deletion: {filenames_after_deletion}")
        assert (
            pdf_path not in filenames_after_deletion
        ), f"File '{pdf_path}' should have been deleted."
    except Exception as e:
        logging.error(f"Error during verification of deletion: {e}")

    logging.info("Test script completed.")


if __name__ == "__main__":
    collection_name = "medical1"
    pdf_path = "src\\data\\sample.pdf"
    main(collection_name, pdf_path)
