from pythainlp import word_vector
from pythainlp.tokenize import word_tokenize
import numpy as np


class Thai2VecEmbedder:
    """
    A class for generating embeddings for Thai text using the Thai2Fit WordVector model.

    This class provides methods to generate embeddings for individual queries or a list of documents
    by averaging the word embeddings of the tokens in the text.
    """

    def __init__(self):
        """
        Initialize the Thai2VecEmbedder.

        Attributes:
            model: A pretrained WordVector model (Thai2Fit) loaded via PyThaiNLP for generating word embeddings.
        """
        self.model = word_vector.WordVector(model_name="thai2fit_wv").get_model()

    def embed_documents(self, documents: list[str]) -> list[np.ndarray | None]:
        """
        Embed a list of documents by averaging the word embeddings of the words in each document.

        Args:
            documents (list[str]): A list of document strings to embed.

        Returns:
            list[np.ndarray | None]: A list of numpy arrays representing the document embeddings.
                                     If a document has no tokens with embeddings, None is returned for that document.
        """
        embeddings = []
        for document in documents:
            tokens = word_tokenize(document)  # Tokenize the document into words
            word_embeddings = [
                self.model[token] for token in tokens if token in self.model
            ]
            if word_embeddings:
                avg_embedding = np.mean(word_embeddings, axis=0)
                embeddings.append(avg_embedding)
            else:
                embeddings.append(None)  # No valid embeddings found for this document
        return embeddings

    def get_embedding(self, query: str) -> np.ndarray | None:
        """
        Generate an embedding for a specific query by averaging the embeddings of its tokens.

        Args:
            query (str): The input query string to embed.

        Returns:
            np.ndarray | None: A numpy array representing the query embedding.
                               If the query has no tokens with embeddings, None is returned.
        """
        tokens = word_tokenize(query)  # Tokenize the query into words
        embeddings = [self.model[token] for token in tokens if token in self.model]
        if embeddings:
            return np.mean(embeddings, axis=0)
        return None  # No valid embeddings found for the query
