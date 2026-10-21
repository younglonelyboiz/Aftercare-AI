from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[5]

DOC_PATHS = {
    "byt_1851": PROJECT_ROOT / "Data" / "raw" / "Hướng-dẫn-chẩn-đoán-và-điều-trị-Hen-phế-quản-người-lớn-và-trẻ-_12-tuổi.pdf",
    "gina_2023": PROJECT_ROOT / "Data" / "GINA-2023-Ban-Dich-Tieng-Viet-Hen-Phe-Quan.pdf",
}

@router.get("/view/{document_tag}")
def view_document_pdf(document_tag: str):
    """Phục vụ file PDF gốc từ Bộ Y Tế hoặc GINA để người dùng mở trực tiếp trang."""
    tag_clean = document_tag.lower().strip()
    pdf_path = DOC_PATHS.get(tag_clean)
    
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu PDF với mã: {document_tag}")
        
    safe_filename = f"{tag_clean}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=safe_filename,
        content_disposition_type="inline"
    )
