import os
from typing import TypedDict, List, Dict, Any, Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from google import genai 

from src.rag_engine.retriever import AsthmaRetriever
from src.rag_engine.prompts import (
    TRIAGE_PROMPT, 
    AFTERCARE_SYSTEM_PROMPT, 
    EMERGENCY_RESPONSE_PROMPT
)

load_dotenv()

# 1. Định nghĩa State của Đồ thị
class AgentState(TypedDict):
    user_query: str
    patient_profile: Dict[str, Any]
    triage_status: str                 
    retrieved_docs: List[Dict[str, Any]]
    rag_context: str
    final_response: str

class AftercareAgentGraph:
    def __init__(self, retriever: AsthmaRetriever):
        self.retriever = retriever
        # Khởi tạo Client 
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = "gemini-3.5-flash-lite" 
        self.graph = self._build_graph()

    def _extract_profile_vars(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        p_info = profile.get("patient_info", {})
        c_status = profile.get("clinical_status", {})
        meds = profile.get("current_medications", {})
        rules = profile.get("action_plan_rules", {})
        f_up = profile.get("follow_up", {})

        best_pef = c_status.get("personal_best_pef", 500)
        return {
            "full_name": p_info.get("full_name", "Bệnh nhân"),
            "age": p_info.get("age", ""),
            "gender": p_info.get("gender", ""),
            "diagnosis": c_status.get("diagnosis", ""),
            "known_triggers": ", ".join(c_status.get("known_triggers", [])),
            "personal_best_pef": best_pef,
            "green_zone_pef": int(best_pef * 0.8),
            "yellow_zone_pef": int(best_pef * 0.6),
            "red_zone_pef": int(best_pef * 0.6),
            "baseline_spo2": c_status.get("baseline_spo2", 98),
            "controller_med": meds.get("controller_med", ""),
            "reliever_med": meds.get("reliever_med", ""),
            "green_zone": rules.get("green_zone", ""),
            "yellow_zone": rules.get("yellow_zone", ""),
            "red_zone": rules.get("red_zone", ""),
            "next_appointment": f_up.get("next_appointment", ""),
            "hospital": f_up.get("hospital", "")
        }

    def triage_node(self, state: AgentState) -> AgentState:
        p_vars = self._extract_profile_vars(state["patient_profile"])
        prompt = TRIAGE_PROMPT.format(user_query=state["user_query"], **p_vars)
        
        # Cú pháp gọi API sinh chữ mới
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        status = response.text.strip().upper()
        
        state["triage_status"] = "RED_ZONE" if "RED_ZONE" in status else "NORMAL"
        return state

    def route_after_triage(self, state: AgentState) -> Literal["emergency_node", "retrieve_node"]:
        if state["triage_status"] == "RED_ZONE":
            return "emergency_node"
        return "retrieve_node"

    def emergency_node(self, state: AgentState) -> AgentState:
        p_vars = self._extract_profile_vars(state["patient_profile"])
        prompt = EMERGENCY_RESPONSE_PROMPT.format(user_query=state["user_query"], **p_vars)
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        state["final_response"] = response.text
        return state

    def retrieve_node(self, state: AgentState) -> AgentState:
        diagnosis = state["patient_profile"]["clinical_status"]["diagnosis"]
        enriched_query = f"{state['user_query']} ({diagnosis})"
        
        docs = self.retriever.retrieve(query=enriched_query, top_k=3)
        state["retrieved_docs"] = docs
        state["rag_context"] = self.retriever.format_context_for_llm(docs)
        return state

    def generate_node(self, state: AgentState) -> AgentState:
        p_vars = self._extract_profile_vars(state["patient_profile"])
        system_instruction = AFTERCARE_SYSTEM_PROMPT.format(rag_context=state["rag_context"], **p_vars)
        
        full_prompt = f"{system_instruction}\n\n### CÂU HỎI CỦA BỆNH NHÂN:\n{state['user_query']}"
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt
        )
        state["final_response"] = response.text
        return state

    def _build_graph(self):
        # (Giữ nguyên hàm này như cũ của bạn)
        workflow = StateGraph(AgentState)
        workflow.add_node("triage_node", self.triage_node)
        workflow.add_node("emergency_node", self.emergency_node)
        workflow.add_node("retrieve_node", self.retrieve_node)
        workflow.add_node("generate_node", self.generate_node)

        workflow.set_entry_point("triage_node")
        workflow.add_conditional_edges(
            "triage_node",
            self.route_after_triage,
            {
                "emergency_node": "emergency_node",
                "retrieve_node": "retrieve_node"
            }
        )
        workflow.add_edge("emergency_node", END)
        workflow.add_edge("retrieve_node", "generate_node")
        workflow.add_edge("generate_node", END)

        return workflow.compile()

    def invoke(self, user_query: str, patient_profile: Dict[str, Any]) -> Dict[str, Any]:
        initial_state: AgentState = {
            "user_query": user_query,
            "patient_profile": patient_profile,
            "triage_status": "NORMAL",
            "retrieved_docs": [],
            "rag_context": "",
            "final_response": ""
        }
        return self.graph.invoke(initial_state)