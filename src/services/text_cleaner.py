import logging
import re
import unicodedata
import tiktoken


class TextCleaner:
    def __init__(self):
        """Initialize the NLPTransformation"""
        self.tokenizer = tiktoken.get_encoding("o200k_base")

    @staticmethod
    def thai_to_arabic(text: str) -> str:
        """Converts Thai numerals in a string to Arabic numerals."""
        thai_to_arabic_map = str.maketrans("๑๒๓๔๕๖๗๘๙๐", "1234567890")
        return text.translate(thai_to_arabic_map)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Applies text normalization: Unicode normalization and lowercase conversion."""
        text = unicodedata.normalize("NFC", text)
        return text.lower()

    @staticmethod
    def remove_unimportant_word(text: str) -> str:
        """Removes extra spaces and normalizes the text, removing single Thai characters inside parentheses."""
        text = re.sub(r"[\n\r\t]+", "", text)
        text = re.sub(r"\s+", "", text).strip()
        text = re.sub(r"\([a-zA-Zก-ฮ]\)", "", text)
        text = re.sub(
            r"([\u0E01-\u0E2E])\s+([\u0E30-\u0E39\u0E47-\u0E4F])", r"\1\2", text
        )
        return text

    def preprocess_text(self, text: str) -> str:
        """Preprocess Thai text (e.g., normalization, segmentation)."""
        text = self.thai_to_arabic(text)
        # text = self.normalize_text(text)
        text = self.remove_unimportant_word(text)
        return text
