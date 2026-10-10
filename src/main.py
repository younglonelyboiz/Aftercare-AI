"""
Main CLI entrypoint for Aftercare-AI Data Processing.
Giao diện dòng lệnh để thực thi các bước trong pipeline xử lý tri thức RAG.
"""

import sys
import argparse
from pathlib import Path

# Đảm bảo đường dẫn import hoạt động đúng khi chạy trực tiếp
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    DEFAULT_PDF_PATH,
    DEFAULT_MD_PATH,
    DEFAULT_RAW_JSON_PATH,
    DEFAULT_COMPACT_JSON_PATH,
)
from src.rag import RAGPipeline

def main():
    parser = argparse.ArgumentParser(
        description="Aftercare-AI: Pipeline xử lý dữ liệu tri thức y khoa RAG cho bệnh Hen phế quản."
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 3],
        help="Chọn bước cần chạy: 1 (PDF -> MD), 2 (MD -> JSON + Embedding), 3 (Chuẩn hóa nén vector JSON)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Chạy toàn bộ pipeline từ Bước 1 đến Bước 3"
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=str(DEFAULT_PDF_PATH),
        help=f"Đường dẫn file PDF đầu vào (mặc định: {DEFAULT_PDF_PATH})"
    )
    parser.add_argument(
        "--md",
        type=str,
        default=str(DEFAULT_MD_PATH),
        help=f"Đường dẫn file Markdown (mặc định: {DEFAULT_MD_PATH})"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=str(DEFAULT_COMPACT_JSON_PATH),
        help=f"Đường dẫn file JSON kết quả (mặc định: {DEFAULT_COMPACT_JSON_PATH})"
    )

    args = parser.parse_args()
    pipeline = RAGPipeline()

    if args.all or (args.step is None and not any([args.step])):
        if args.all:
            pipeline.run_all(
                pdf_path=args.pdf,
                md_path=args.md,
                raw_json_path=DEFAULT_RAW_JSON_PATH,
                final_json_path=args.output_json
            )
        else:
            parser.print_help()
            print("\nVí dụ sử dụng:")
            print("  python src/main.py --step 1        # Chạy trích xuất PDF sang Markdown")
            print("  python src/main.py --step 2        # Chạy phân đoạn, gán nhãn và tạo vector")
            print("  python src/main.py --step 3        # Nén dòng vector trong JSON")
            print("  python src/main.py --all           # Chạy toàn bộ quy trình")
            return

    elif args.step == 1:
        pipeline.step1_convert_pdf_to_md(pdf_path=args.pdf, output_md_path=args.md)

    elif args.step == 2:
        pipeline.step2_process_markdown_to_json(
            input_md_path=args.md,
            output_json_path=args.output_json,
            compact_output=True
        )

    elif args.step == 3:
        pipeline.step3_compact_json_vectors(
            input_json_path=DEFAULT_RAW_JSON_PATH if Path(DEFAULT_RAW_JSON_PATH).exists() else args.output_json,
            output_json_path=args.output_json
        )

if __name__ == "__main__":
    main()

