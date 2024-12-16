from utilities.text_utils import thai_to_arabic, normalize_text, remove_unimportant_word
import tiktoken


class TextCleaner:
    def __init__(self):
        """Initialize the NLPTransformation"""
        self.tokenizer = tiktoken.get_encoding("o200k_base")

    def preprocess_text(self, text: str) -> str:
        """Preprocess Thai text (e.g., normalization, segmentation)."""
        text = thai_to_arabic(text)
        # text = self.normalize_text(text)
        text = remove_unimportant_word(text)
        return text
