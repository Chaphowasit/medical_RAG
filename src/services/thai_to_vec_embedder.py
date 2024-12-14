from pythainlp import word_vector
from pythainlp.tokenize import word_tokenize
import numpy as np


class Thai2VecEmbedder:
    def __init__(self):
        self.model = word_vector.WordVector(model_name="thai2fit_wv").get_model()

    def embed_documents(self, documents):
        """Embed a list of documents by averaging word embeddings of the words in each document."""
        embeddings = []
        for document in documents:
            tokens = word_tokenize(document)
            word_embeddings = [
                self.model[token] for token in tokens if token in self.model
            ]
            if word_embeddings:
                avg_embedding = np.mean(word_embeddings, axis=0)
                embeddings.append(avg_embedding)
            else:
                embeddings.append(None)  # In case no words are found in the model
        return embeddings

    def get_embedding(self, query: str):
        tokens = word_tokenize(query)
        # Average word embeddings of tokens in the query
        embeddings = [self.model[token] for token in tokens if token in self.model]
        if embeddings:
            return np.mean(embeddings, axis=0)
        return None
