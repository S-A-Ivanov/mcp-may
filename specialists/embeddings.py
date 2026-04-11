import os
import requests
import logging
from typing import List, Union
class UniversalEmbeddingFunction:
    """#S_EN: [ENGINE] Универсальный мост для векторов через Gateway."""
    
    def __init__(self, gateway, model_name=None):
        self.gateway = gateway
        # Берем модель из конфига, если не передана явно
        self.model_name = model_name or gateway.cfg['routing']['embeddings']['model']

    def name(self) -> str:
        """#S_EN: [REQUIRED] Метод для совместимости с ChromaDB."""
        return f"UniversalEmbedding_{self.model_name.replace(':', '_')}"

    def __call__(self, input: Union[str, List[str]]) -> List[List[float]]:
        # ChromaDB присылает список строк
        texts = [input] if isinstance(input, str) else input
        return [self.gateway.get_embeddings(text, model=self.model_name) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        return self.gateway.get_embeddings(query, model=self.model_name)
    
    def __repr__(self):
        return f"<UniversalEmbeddingFunction(model='{self.model_name}')>"
