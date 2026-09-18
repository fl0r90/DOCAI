import os
import torch
from sentence_transformers import CrossEncoder

class RerankService:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            default_device = "cuda" if torch.cuda.is_available() else "cpu"
            device = os.getenv("RERANKER_DEVICE", default_device)
            model_name = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
            print(f"[*] Initializing Reranker ({model_name}) on {device}...")
            try:
                # Force local HF hub cache path matching Docker environment
                os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
                cls._instance = cls(model_name=model_name, device=device)
            except Exception as e:
                print(f"[!] Error loading Reranker on {device}: {e}")
                if device == "cuda":
                    print("[*] Falling back to CPU for Reranker...")
                    try:
                        cls._instance = cls(model_name=model_name, device="cpu")
                    except Exception as e2:
                        print(f"[!] Fatal error loading CPU Reranker: {e2}")
                        raise e2
                else:
                    raise e
        return cls._instance

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu"):
        # We load high-precision multilingual cross-encoder BAAI/bge-reranker-v2-m3
        self.device = device
        self.model = CrossEncoder(model_name, device=device)

    def rerank(self, query: str, candidates: list, top_k: int = 10) -> list:
        """
        Rerank document chunk candidates based on cross-encoder similarity.
        candidates: List of DocumentChunk models/objects.
        Returns: List of tuples (score, DocumentChunk) sorted by score descending.
        """
        if not candidates:
            return []
        
        # Form input pairs
        pairs = [[query, c.content] for c in candidates]
        
        try:
            # Predict scores (higher is more relevant) with batch_size=32 for GPU parallelism
            scores = self.model.predict(pairs, batch_size=32)
            
            # Combine candidates with scores
            scored_candidates = list(zip(scores, candidates))
            
            # Sort by score descending
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            return scored_candidates[:top_k]
        except Exception as e:
            print(f"[!] Error during reranking prediction: {e}")
            # Fallback to returning original candidates with dummy scores
            return [(0.0, c) for c in candidates[:top_k]]
