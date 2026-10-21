"""
BGE-M3 Embedding Service for Aftercare-AI.
Sử dụng mô hình BAAI/bge-m3 để tạo Dense Vector 1024 chiều (chuẩn y tế đa ngữ Anh - Việt).
Hỗ trợ tự động nhận diện thiết bị CUDA GPU hoặc CPU.
"""

import os
import torch
from typing import List, Union
from sentence_transformers import SentenceTransformer

class BGEM3Embedder:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton pattern để tránh load model nhiều lần vào RAM/VRAM
        if cls._instance is None:
            cls._instance = super(BGEM3Embedder, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = None,
        max_seq_length: int = 8192
    ):
        if getattr(self, "_initialized", False):
            return

        self.model_name = model_name
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"[BGEM3Embedder] Đang khởi tạo mô hình '{self.model_name}' trên thiết bị: {self.device}...")
        
        # Với GPU 4GB VRAM: dùng fp16 và giới hạn max_seq_length = 1024 tokens (đủ lớn cho chunk 1200 ký tự)
        model_kwargs = {}
        if self.device == "cuda":
            model_kwargs = {"torch_dtype": torch.float16}
            torch.cuda.empty_cache()

        self.model = SentenceTransformer(
            self.model_name, 
            device=self.device,
            model_kwargs=model_kwargs
        )
        self.model.max_seq_length = min(max_seq_length, 1024)
        self._initialized = True
        print(f"[BGEM3Embedder] Khởi tạo thành công! Chiều vector: 1024, Context: {self.model.max_seq_length} tokens, fp16={self.device=='cuda'}.")

    def embed_text(self, text: str) -> List[float]:
        """Tạo dense vector 1024 chiều cho một đoạn văn bản đơn lẻ."""
        if not text or not text.strip():
            return [0.0] * 1024
        with torch.no_grad():
            embedding = self.model.encode(
                text,
                batch_size=1,
                show_progress_bar=False,
                normalize_embeddings=True
            )
        return embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 4,
        show_progress_bar: bool = True
    ) -> List[List[float]]:
        """Tạo vector 1024 chiều theo lô (batch_size=4 chống OOM cho GPU 4GB)."""
        if not texts:
            return []
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                normalize_embeddings=True
            )
        if self.device == "cuda":
            torch.cuda.empty_cache()
        return embeddings.tolist()

if __name__ == "__main__":
    embedder = BGEM3Embedder()
    test_query = "Bệnh nhân hen bậc 2 cần xử trí thuốc gì khi khó thở đột ngột?"
    vector = embedder.embed_text(test_query)
    print(f"Kiểm tra vector: Độ dài = {len(vector)}, 5 giá trị đầu = {vector[:5]}")
