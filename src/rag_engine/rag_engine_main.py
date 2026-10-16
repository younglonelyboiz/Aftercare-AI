import json
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.rag_engine.retriever import AsthmaRetriever
from src.rag_engine.graph import AftercareAgentGraph
from src.config import QDRANT_COLLECTION_NAME
PROFILES = {
    "1": "Data/patient_profiles/patient_1_mild.json",
    "2": "Data/patient_profiles/patient_2_severe.json",
    "3": "Data/patient_profiles/patient_3_special.json"
}

def load_patient_profile(choice: str) -> dict:
    filepath = PROFILES.get(choice, PROFILES["1"])
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Không tìm thấy hồ sơ tại: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    print("=" * 60)
    print("HỆ THỐNG AFTERCARE")
    print("=" * 60)
    print("Chọn kịch bản hồ sơ bệnh nhân để mô phỏng:")
    print("  [1] Kịch bản 1: Bệnh nhân hen nhẹ (Nguyễn Văn An)")
    print("  [2] Kịch bản 2: Bệnh nhân hen nặng (Test cờ đỏ)")
    print("  [3] Kịch bản 3: Bệnh nhân có yếu tố đặc thù")
    
    choice = input("\nNhập lựa chọn (1/2/3, mặc định 1): ").strip() or "1"
    profile = load_patient_profile(choice)
    p_info = profile["patient_info"]
    c_status = profile["clinical_status"]

    print(f"\nĐã tải hồ sơ: {p_info['full_name']} ({p_info['age']} tuổi) - {c_status['diagnosis']}")
    print(f"PEF tốt nhất: {c_status['personal_best_pef']} L/phút (Vùng đỏ < {int(c_status['personal_best_pef']*0.6)} L/phút)")
    print("-" * 60)

    # Khởi tạo Retriever & LangGraph Agent
    # Lưu ý: Kiểm tra lại tên collection_name lúc bạn viết trong ingest_to_qdrant.py
    retriever = AsthmaRetriever(
        qdrant_path="Data/qdrant_db",
        collection_name=QDRANT_COLLECTION_NAME
    )
    agent = AftercareAgentGraph(retriever=retriever)

    print("Nhập 'exit' để thoát. Hãy thử hỏi về cách dùng thuốc hoặc báo chỉ số PEF!\n")

    while True:
        user_query = input(f"{p_info['full_name']}: ").strip()
        if user_query.lower() in ["exit", "quit", "thoát"]:
            break
        if not user_query:
            continue

        result = agent.invoke(user_query=user_query, patient_profile=profile)

        print(f"\n[Trạng thái phân loại: {result['triage_status']}]")
        if result["retrieved_docs"]:
            citations = [doc["citation_tag"] for doc in result["retrieved_docs"]]
            print(f"[Tài liệu tham chiếu: {', '.join(citations)}]")
            
        print(f"\nAftercare AI:\n{result['final_response']}\n")
        print("-" * 60)

if __name__ == "__main__":
    main()