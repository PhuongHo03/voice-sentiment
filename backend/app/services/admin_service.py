from datetime import datetime
from fastapi import HTTPException, status
import httpx

from app.configs.cache import RedisJobCache
from app.configs.config import settings
from app.models.models import UserModel
from app.repositories.admin_repository import AdminRepository
from app.repositories.analysis_repository import SqlAlchemyAnalysisRepository


class AdminService:
    def __init__(self, repository: AdminRepository, analysis_repository: SqlAlchemyAnalysisRepository):
        self.repository = repository
        self.analysis_repository = analysis_repository

    def get_employees(self) -> dict:
        employees = self.repository.list_employees()
        return {"employees": [self._build_employee_stats(emp) for emp in employees]}

    def get_employee_stats(self, employee_id: str) -> dict:
        self._require_employee(employee_id)
        return self.analysis_repository.get_analytics_stats(owner_id=employee_id)

    def get_employee_sessions(self, employee_id: str) -> dict:
        self._require_employee(employee_id)
        jobs = self.repository.list_employee_sessions(employee_id)
        sessions_list = []
        for job, result in jobs:
            sessions_list.append({
                "job_id": str(job.id),
                "name": job.name,
                "status": job.status,
                "input_type": job.input_type,
                "created_at": job.created_at,
                "sentiment": result.sentiment if result else None,
                "confidence": result.confidence if result else None,
                "agent_score": result.agent_score if result else None,
                "agent_advice": result.agent_advice_json if result else None,
                "summary": result.summary_json if result else None,
                "sentiment_reason": result.sentiment_reason if result else None,
                "transcript": result.transcript_json if result else None,
            })
        return {"sessions": sessions_list}

    def get_all_users(self) -> dict:
        result = []
        for user in self.repository.list_users():
            result.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role_id": user.role_id,
                "is_active": user.is_active,
                "created_at": user.created_at,
            })
        return {"users": result}

    def update_user_status(self, user_id: str, is_active: bool, current_admin: UserModel) -> dict:
        if user_id == current_admin.id and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự vô hiệu hóa tài khoản Admin đang đăng nhập.",
            )

        user = self.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user = self.repository.update_user_status(user, is_active)
        action = "kích hoạt" if is_active else "vô hiệu hóa"
        return {
            "message": f"Tài khoản '{user.username}' đã được {action} thành công.",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active,
                "role_id": user.role_id,
            },
        }

    def update_user_role(self, user_id: str, role_id: str, current_admin: UserModel) -> dict:
        role = self.repository.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vai trò '{role_id}' không tồn tại trong hệ thống.",
            )

        user = self.repository.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user_id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tự đổi vai trò của tài khoản Admin đang đăng nhập.",
            )

        user = self.repository.replace_user_role(user, role_id)
        return {
            "message": f"Đã cập nhật vai trò của '{user.username}' thành '{role.name}'.",
            "user": {
                "id": user.id,
                "username": user.username,
                "is_active": user.is_active,
                "role_id": user.role_id,
            },
        }

    def _build_employee_stats(self, emp: UserModel) -> dict:
        avg_score = self.repository.get_employee_average_score(emp.id)
        avg_score = round(float(avg_score), 1) if avg_score is not None else None

        sentiments = {"positive": 0, "neutral": 0, "negative": 0}
        for sent, count in self.repository.get_employee_sentiment_counts(emp.id):
            if sent and sent.lower() in sentiments:
                sentiments[sent.lower()] = count

        return {
            "id": emp.id,
            "username": emp.username,
            "email": emp.email,
            "total_jobs": self.repository.get_employee_job_count(emp.id),
            "average_score": avg_score,
            "sentiment_distribution": sentiments,
            "created_at": emp.created_at,
        }

    def _require_employee(self, employee_id: str) -> None:
        if not self.repository.has_employee_role(employee_id):
            raise HTTPException(status_code=404, detail="Employee not found")

    def get_system_metrics(self) -> dict:
        cache = RedisJobCache()
        cached = cache.get_metrics_snapshot()
        if cached:
            return cached

        monitored_jobs = ["backend", "voice-worker", "llm-worker", "postgres", "redis", "rabbitmq", "nginx"]

        def query_prom(client: httpx.Client, query: str) -> dict:
            try:
                resp = client.get(
                    f"{settings.prometheus_url}/api/v1/query",
                    params={"query": query},
                    timeout=2.0,
                )
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                pass
            return {"status": "error", "data": {"result": []}}

        try:
            with httpx.Client() as client:
                up_data = query_prom(client, 'up{job=~"backend|voice-worker|llm-worker|postgres|redis|rabbitmq|nginx"}')
                req_rate_data = query_prom(client, "sum(rate(voice_sentiment_http_requests_total[5m]))")
                err_rate_data = query_prom(client, 'sum(rate(voice_sentiment_http_requests_total{status=~"5.."}[5m]))')
                latency_data = query_prom(
                    client,
                    "histogram_quantile(0.95, sum(rate(voice_sentiment_http_request_duration_seconds_bucket[5m])) by (le))"
                )
                job_rate_data = query_prom(client, "sum(rate(voice_sentiment_llm_jobs_total[5m]))")

            # 1. Parse service health
            up_results = up_data.get("data", {}).get("result", [])
            service_health = []
            down_count = 0
            for job in monitored_jobs:
                item = next((r for r in up_results if r.get("metric", {}).get("job") == job), None)
                is_up = False
                if item:
                    val = item.get("value", [0, "0"])[1]
                    try:
                        is_up = float(val) == 1.0
                    except ValueError:
                        pass

                if not is_up:
                    down_count += 1

                service_health.append(
                    {
                        "job": job,
                        "up": is_up,
                        "detail": "Đang scrape" if is_up else ("Mất scrape" if item else "Chưa có target"),
                    }
                )

            # 2. Parse numbers
            def parse_val(data: dict) -> float:
                res = data.get("data", {}).get("result", [])
                if res and len(res) > 0:
                    val = res[0].get("value", [0, "0"])[1]
                    try:
                        parsed = float(val)
                        return parsed if parsed >= 0 else 0.0
                    except ValueError:
                        pass
                return 0.0

            req_rate = parse_val(req_rate_data)
            err_rate = parse_val(err_rate_data)
            latency = parse_val(latency_data)
            job_rate = parse_val(job_rate_data)

            # 3. Format values
            def format_rate(val: float) -> str:
                return f"{val:.2f}/s"

            def format_seconds(val: float) -> str:
                if val >= 1.0:
                    return f"{val:.2f}s"
                return f"{int(round(val * 1000))}ms"

            cards = [
                {
                    "label": "Targets online",
                    "value": f"{len(monitored_jobs) - down_count}/{len(monitored_jobs)}",
                    "status": "ok" if down_count == 0 else "error",
                    "detail": (
                        "Tất cả target đang được Prometheus scrape"
                        if down_count == 0
                        else f"{down_count} target đang down"
                    ),
                },
                {
                    "label": "Request rate",
                    "value": format_rate(req_rate),
                    "status": "ok",
                    "detail": "Tổng HTTP request 5 phút gần nhất",
                },
                {
                    "label": "5xx rate",
                    "value": format_rate(err_rate),
                    "status": "warn" if err_rate > 0 else "ok",
                    "detail": "Tổng lỗi HTTP 5xx 5 phút gần nhất",
                },
                {
                    "label": "P95 latency",
                    "value": format_seconds(latency),
                    "status": "warn" if latency > 2.0 else "ok",
                    "detail": "P95 latency từ service HTTP metrics",
                },
                {
                    "label": "LLM jobs",
                    "value": format_rate(job_rate),
                    "status": "ok",
                    "detail": "Tốc độ xử lý job worker 5 phút gần nhất",
                },
            ]

            metrics = {
                "serviceHealth": service_health,
                "cards": cards,
                "lastUpdated": datetime.now().strftime("%H:%M:%S"),
            }

            cache.set_metrics_snapshot(metrics)
            return metrics

        except Exception as e:
            import logging

            logger = logging.getLogger("admin_service_metrics")
            logger.error(f"Failed to fetch system metrics from Prometheus: {str(e)}")
            service_health = [{"job": job, "up": False, "detail": "Lỗi kết nối Prometheus"} for job in monitored_jobs]
            cards = [
                {"label": "Targets online", "value": "0/7", "status": "error", "detail": f"Lỗi Prometheus: {str(e)}"},
                {"label": "Request rate", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "5xx rate", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "P95 latency", "value": "0ms", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "LLM jobs", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
            ]
            return {
                "serviceHealth": service_health,
                "cards": cards,
                "lastUpdated": datetime.now().strftime("%H:%M:%S"),
            }
