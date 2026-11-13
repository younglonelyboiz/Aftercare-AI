"""
Decorator bảo vệ nút đồ thị theo nguyên tắc Fail-closed (INV-4) — [W07-T1.3].

Mọi nút trong đồ thị đều được bọc bởi `@safe_node`:
1. Đo thời gian thực thi (tính bằng mili-giây) và ghi vào `state["latency_ms"][node_name]`.
2. Nếu nút ném ngoại lệ (trừ ngoại lệ nghiệp vụ được cho phép đi qua như `PatientNotFoundError`
   hoặc `RiskDowngradeError`), ngoại lệ được ghi vào nhật ký hệ thống, cờ `error` và `degraded`
   được bật, đồng thời thêm một `GuardEvent` có `decision="FALLBACK"` để đồ thị chuyển sang
   nút `safe_fallback`.
"""
import functools
import logging
import time
from typing import Any, Callable, Dict, Tuple, Type

from backend.app.orchestration.state import (
    AftercareState,
    RiskDowngradeError,
    append_guard_event,
)

logger = logging.getLogger("OrchestrationSafeNode")


class PatientNotFoundError(ValueError):
    """Ngoại lệ khi không tìm thấy hồ sơ bệnh nhân (tương ứng mã HTTP 404)."""


PASSTHROUGH_EXCEPTIONS: Tuple[Type[BaseException], ...] = (
    PatientNotFoundError,
    RiskDowngradeError,
)


def safe_node(node_name: str, layer: str = "ORCHESTRATION"):
    """Bọc một hàm nút đồ thị để đo độ trễ và cưỡng chế Fail-closed khi gặp sự cố."""

    def decorator(func: Callable[[AftercareState], Dict[str, Any]]):
        @functools.wraps(func)
        def wrapper(state: AftercareState) -> Dict[str, Any]:
            start_time = time.perf_counter()
            latency_map = dict(state.get("latency_ms") or {})
            try:
                updates = func(state) or {}
                elapsed_ms = max(0, int((time.perf_counter() - start_time) * 1000))
                merged_latency = dict(updates.get("latency_ms") or latency_map)
                merged_latency[node_name] = elapsed_ms
                updates["latency_ms"] = merged_latency
                return updates
            except PASSTHROUGH_EXCEPTIONS:
                raise
            except Exception as exc:
                elapsed_ms = max(0, int((time.perf_counter() - start_time) * 1000))
                latency_map[node_name] = elapsed_ms
                logger.exception(
                    "Lỗi tại nút đồ thị '%s' (trace_id=%s, patient_id=%s)",
                    node_name,
                    state.get("trace_id"),
                    state.get("patient_id"),
                )
                events = append_guard_event(
                    state,
                    layer=layer,
                    rule_id=f"SYS-NODE-ERROR:{node_name}",
                    decision="FALLBACK",
                    detail=f"Nút '{node_name}' gặp sự cố nội bộ ({type(exc).__name__}).",
                )
                return {
                    "error": f"{node_name}:{type(exc).__name__}",
                    "degraded": True,
                    "latency_ms": latency_map,
                    "guard_events": events,
                }

        return wrapper

    return decorator

