import re
import unicodedata
from langchain_text_splitters import RecursiveCharacterTextSplitter


def text_splitter(docs: str):
    """
    Splits a blog post or document into smaller sub-documents using RecursiveCharacterTextSplitter.

    Args:
        docs (str): The input document or blog post as a single string.

    Returns:
        None: This function prints the number of sub-documents created but does not return anything.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    all_splits = text_splitter.split_documents(docs)

    print(f"Split blog post into {len(all_splits)} sub-documents.")


def thai_to_arabic(text: str) -> str:
    """
    Converts Thai numerals in a string to Arabic numerals.

    Args:
        text (str): The input string potentially containing Thai numerals.

    Returns:
        str: The string with Thai numerals replaced by Arabic numerals.
    """
    thai_to_arabic_map = str.maketrans("๑๒๓๔๕๖๗๘๙๐", "1234567890")
    return text.translate(thai_to_arabic_map)


def normalize_text(text: str) -> str:
    """
    Normalizes a string by applying Unicode normalization and converting it to lowercase.

    Args:
        text (str): The input string to be normalized.

    Returns:
        str: The normalized string in lowercase.
    """
    text = unicodedata.normalize("NFC", text)
    return text.lower()


def remove_unimportant_word(text: str) -> str:
    """
    Removes unnecessary characters, extra spaces, and single Thai characters inside parentheses from the text.

    Args:
        text (str): The input text string to clean and normalize.

    Returns:
        str: The cleaned and normalized text string.
    """
    text = re.sub(r"[\n\r\t]+", "", text)  # Remove newlines, carriage returns, and tabs
    text = re.sub(r"\s+", "", text).strip()  # Remove extra spaces
    text = re.sub(r"\([a-zA-Zก-ฮ]\)", "", text)  # Remove single characters in parentheses
    text = re.sub(r"([\u0E01-\u0E2E])\s+([\u0E30-\u0E39\u0E47-\u0E4F])", r"\1\2", text)  # Fix Thai character spacing
    return text
