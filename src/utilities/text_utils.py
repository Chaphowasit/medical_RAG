import re
import unicodedata

from langchain_text_splitters import RecursiveCharacterTextSplitter


def text_splitter(docs: str):
    """Split a blog post into sub-documents using RecursiveCharacterTextSplitter."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    all_splits = text_splitter.split_documents(docs)

    print(f"Split blog post into {len(all_splits)} sub-documents.")


def thai_to_arabic(text: str) -> str:
    """Converts Thai numerals in a string to Arabic numerals."""
    thai_to_arabic_map = str.maketrans("๑๒๓๔๕๖๗๘๙๐", "1234567890")
    return text.translate(thai_to_arabic_map)


def normalize_text(text: str) -> str:
    """Applies text normalization: Unicode normalization and lowercase conversion."""
    text = unicodedata.normalize("NFC", text)
    return text.lower()


def remove_unimportant_word(text: str) -> str:
    """Removes extra spaces and normalizes the text, removing single Thai characters inside parentheses."""
    text = re.sub(r"[\n\r\t]+", "", text)
    text = re.sub(r"\s+", "", text).strip()
    text = re.sub(r"\([a-zA-Zก-ฮ]\)", "", text)
    text = re.sub(r"([\u0E01-\u0E2E])\s+([\u0E30-\u0E39\u0E47-\u0E4F])", r"\1\2", text)
    return text
