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

    def get_employees(self, current_user: UserModel) -> dict:
        employees = self.repository.list_all_users_with_performance()
        # Sort: current user first
        def sort_key(emp: UserModel):
            return (emp.id != current_user.id, emp.created_at)
        employees.sort(key=sort_key, reverse=True)
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
        user = self.repository.get_user(employee_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

    def get_system_metrics(self) -> dict:
        cache = RedisJobCache()
        cached = cache.get_metrics_snapshot()
        if cached:
            return cached

        monitored_jobs = ["backend", "frontend", "voice-worker", "llm-worker", "postgres", "redis", "rabbitmq", "nginx", "minio"]

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
                up_data = query_prom(client, 'up{job=~"backend|voice-worker|llm-worker|postgres|redis|rabbitmq|nginx|minio"}')
                req_rate_data = query_prom(client, "sum(rate(voice_sentiment_http_requests_total[5m]))")
                err_rate_data = query_prom(client, 'sum(rate(voice_sentiment_http_requests_total{status=~"5.."}[5m]))')
                latency_data = query_prom(
                    client,
                    "histogram_quantile(0.95, sum(rate(voice_sentiment_http_request_duration_seconds_bucket[5m])) by (le))"
                )
                llm_job_rate_data = query_prom(client, "sum(increase(voice_sentiment_llm_jobs_total[5m]))")
                voice_job_rate_data = query_prom(client, "sum(increase(voice_sentiment_voice_transcriptions_total[5m]))")
                postgres_db_size_data = query_prom(client, "sum(pg_database_size_bytes)")
                redis_memory_data = query_prom(client, "redis_memory_used_bytes")
                rabbitmq_messages_data = query_prom(client, "sum(rabbitmq_queue_messages)")
                minio_usage_data = query_prom(client, "minio_cluster_usage_total_bytes")

                # New metrics from Blackbox and Nginx exporter
                blackbox_success_data = query_prom(client, 'avg_over_time(probe_success{instance="http://nginx/health"}[5m]) * 100')
                blackbox_duration_data = query_prom(client, 'probe_duration_seconds{instance="http://nginx/health"}')
                blackbox_ssl_expiry_data = query_prom(client, 'probe_ssl_earliest_cert_expiry{instance="http://nginx/health"} - time()')
                
                nginx_active_conn_data = query_prom(client, 'nginx_connections_active')
                nginx_reading_conn_data = query_prom(client, 'nginx_connections_reading')
                nginx_writing_conn_data = query_prom(client, 'nginx_connections_writing')
                nginx_waiting_conn_data = query_prom(client, 'nginx_connections_waiting')

            # 1. Parse service health
            up_results = up_data.get("data", {}).get("result", [])
            service_health = []
            down_count = 0
            down_services = []
            for job in monitored_jobs:
                scrape_job = "nginx" if job == "frontend" else job
                item = next((r for r in up_results if r.get("metric", {}).get("job") == scrape_job), None)
                is_up = False
                if item:
                    val = item.get("value", [0, "0"])[1]
                    try:
                        is_up = float(val) == 1.0
                    except ValueError:
                        pass

                if not is_up:
                    down_count += 1
                    down_services.append(job)

                service_health.append(
                    {
                        "job": job,
                        "up": is_up,
                        "detail": "Đang scrape" if is_up else ("Mất scrape" if item else "Chưa có target"),
                    }
                )

            # Generate system alerts based on down services
            alerts = []
            for service in down_services:
                alerts.append({
                    "level": "error",
                    "message": f"Dịch vụ {service} đã mất kết nối!"
                })

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

            def parse_val_optional(data: dict) -> float | None:
                res = data.get("data", {}).get("result", [])
                if res and len(res) > 0:
                    val = res[0].get("value", [0, "0"])[1]
                    try:
                        return float(val)
                    except ValueError:
                        pass
                return None

            req_rate = parse_val(req_rate_data)
            err_rate = parse_val(err_rate_data)
            latency = parse_val(latency_data)
            llm_job_rate = parse_val(llm_job_rate_data) / 300.0  # increase over 5m → per-second rate
            voice_job_rate = parse_val(voice_job_rate_data) / 300.0  # increase over 5m → per-second rate
            postgres_db_size = parse_val(postgres_db_size_data)
            redis_memory = parse_val(redis_memory_data)
            rabbitmq_messages = parse_val(rabbitmq_messages_data)
            minio_usage = parse_val(minio_usage_data)

            # Parse new values
            bb_uptime = parse_val(blackbox_success_data)
            bb_latency = parse_val(blackbox_duration_data)
            bb_ssl = parse_val_optional(blackbox_ssl_expiry_data)

            nginx_active = parse_val(nginx_active_conn_data)
            nginx_reading = parse_val(nginx_reading_conn_data)
            nginx_writing = parse_val(nginx_writing_conn_data)
            nginx_waiting = parse_val(nginx_waiting_conn_data)

            # 3. Format values
            def format_rate(val: float) -> str:
                if val < 0.01:
                    return f"{val:.3f}/s"
                return f"{val:.2f}/s"

            def format_seconds(val: float) -> str:
                if val >= 1.0:
                    return f"{val:.2f}s"
                return f"{int(round(val * 1000))}ms"

            def format_bytes(val: float) -> str:
                units = ["B", "KB", "MB", "GB", "TB"]
                size = val
                unit = units[0]
                for unit in units:
                    if size < 1024 or unit == units[-1]:
                        break
                    size /= 1024
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"

            ssl_days = int(bb_ssl / 86400) if bb_ssl is not None else None
            ssl_value = f"{ssl_days} ngày" if ssl_days is not None else "Không dùng SSL"
            ssl_status = "ok"
            if ssl_days is not None:
                if ssl_days < 7:
                    ssl_status = "error"
                elif ssl_days < 15:
                    ssl_status = "warn"

            cards = [
                {
                    "label": "Targets online",
                    "value": f"{len(monitored_jobs) - down_count}/{len(monitored_jobs)}",
                    "status": "ok" if down_count == 0 else "error",
                    "detail": (
                        "Tất cả target đang được Prometheus scrape"
                        if down_count == 0
                        else f"{down_count} target đang down ({', '.join(down_services)})"
                    ),
                },
                {
                    "label": "HTTP Availability",
                    "value": f"{bb_uptime:.2f}%",
                    "status": "ok" if bb_uptime > 99.0 else ("warn" if bb_uptime > 95.0 else "error"),
                    "detail": "Độ khả dụng HTTP (Uptime 5m)",
                },
                {
                    "label": "External Ping",
                    "value": format_seconds(bb_latency),
                    "status": "ok" if bb_latency < 0.5 else ("warn" if bb_latency < 1.5 else "error"),
                    "detail": "Độ trễ kết nối từ bên ngoài",
                },
                {
                    "label": "SSL Certificate",
                    "value": ssl_value,
                    "status": ssl_status,
                    "detail": "Hạn chứng chỉ bảo mật HTTPS",
                },
                {
                    "label": "Active Connections",
                    "value": f"{int(nginx_active)}",
                    "status": "ok",
                    "detail": f"Đọc/Ghi/Chờ: {int(nginx_reading)}/{int(nginx_writing)}/{int(nginx_waiting)}",
                },
                {
                    "label": "Voice jobs",
                    "value": format_rate(voice_job_rate),
                    "status": "ok",
                    "detail": "Tốc độ xử lý job voice worker 5 phút gần nhất",
                },
                {
                    "label": "LLM jobs",
                    "value": format_rate(llm_job_rate),
                    "status": "ok",
                    "detail": "Tốc độ xử lý job LLM worker 5 phút gần nhất",
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
                    "label": "API P95",
                    "value": format_seconds(latency),
                    "status": "warn" if latency > 2.0 else "ok",
                    "detail": "Độ trễ API p95 5 phút gần nhất",
                },
                {"label": "MinIO storage used", "value": format_bytes(minio_usage), "status": "ok", "detail": "Tổng dung lượng object đang lưu"},
                {"label": "Postgres size", "value": format_bytes(postgres_db_size), "status": "ok", "detail": "Tổng dung lượng database"},
                {"label": "Redis memory", "value": format_bytes(redis_memory), "status": "ok", "detail": "Bộ nhớ Redis đang dùng"},
                {"label": "RabbitMQ messages", "value": f"{int(rabbitmq_messages)}", "status": "ok", "detail": "Tổng message đang nằm trong queue"},
            ]

            service_metrics = []

            metrics = {
                "serviceHealth": service_health,
                "cards": cards,
                "serviceMetrics": service_metrics,
                "alerts": alerts,
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
                {"label": "Targets online", "value": "0/9", "status": "error", "detail": f"Lỗi Prometheus: {str(e)}"},
                {"label": "HTTP Availability", "value": "0.00%", "status": "error", "detail": "Không có dữ liệu"},
                {"label": "External Ping", "value": "0ms", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "SSL Certificate", "value": "Không dùng SSL", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "Active Connections", "value": "0", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "Voice jobs", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "LLM jobs", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "Request rate", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "5xx rate", "value": "0.00/s", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "API P95", "value": "0ms", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "MinIO storage used", "value": "0 B", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "Postgres size", "value": "0 B", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "Redis memory", "value": "0 B", "status": "ok", "detail": "Không có dữ liệu"},
                {"label": "RabbitMQ messages", "value": "0", "status": "ok", "detail": "Không có dữ liệu"},
            ]
            return {
                "serviceHealth": service_health,
                "cards": cards,
                "serviceMetrics": [],
                "alerts": [{"level": "error", "message": f"Lỗi hệ thống giám sát: {str(e)}"}],
                "lastUpdated": datetime.now().strftime("%H:%M:%S"),
            }
