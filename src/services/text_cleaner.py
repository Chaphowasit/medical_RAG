from utilities.text_utils import thai_to_arabic, normalize_text, remove_unimportant_word
import tiktoken


class TextCleaner:
    """
    A utility class for cleaning and preprocessing Thai text.

    This class provides methods for text normalization, removing unimportant words,
    and converting Thai numerical expressions to Arabic numerals.
    """

    def __init__(self):
        """
        Initialize the TextCleaner class.

        Attributes:
            tokenizer: A tokenizer object from the `tiktoken` library for tokenizing text.
        """
        self.tokenizer = tiktoken.get_encoding("o200k_base")

    def preprocess_text(self, text: str) -> str:
        """
        Preprocess Thai text by applying various cleaning and transformation operations.

        Args:
            text (str): The input text string to be preprocessed.

        Returns:
            str: The cleaned and preprocessed text.
        """
        text = thai_to_arabic(text)  # Convert Thai numerals to Arabic numerals
        # text = normalize_text(text)  # (Optional) Normalize text structure
        text = remove_unimportant_word(text)  # Remove unimportant or stop words
        return text
