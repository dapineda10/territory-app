import bcrypt
import secrets
from datetime import date, datetime, timedelta, timezone
from supabase import Client


class AuthRepository:
    def __init__(self, client: Client):
        self.client = client
        self._init_admin()

    def _init_admin(self):
        response = self.client.table("users").select("id").eq("username", "admin").execute()
        if not response.data: 
            pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            self.client.table("users").insert({
                "username": "admin",
                "password_hash": pw,
                "role": "admin",
                "sector": "",
            }).execute()

    # ── Auth ──────────────────────────────────────────────────────────────

    def verify(self, username: str, password: str) -> dict | None:
        response = self.client.table("users").select("id, password_hash, role, sector").eq("username", username).execute()
        if not response.data:
            return None
        row = response.data[0]
        if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            return {"id": row["id"], "username": username, "role": row["role"], "sector": row.get("sector") or ""}
        return None

    # ── Sessions ──────────────────────────────────────────────────────────

    def create_session(self, user_id: int, days: int = 30) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        self.client.table("sessions").insert({
            "token": token,
            "user_id": user_id,
            "expires_at": expires,
        }).execute()
        return token

    def validate_session(self, token: str) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        session_resp = self.client.table("sessions").select("user_id").eq("token", token).gt("expires_at", now).execute()
        if not session_resp.data:
            return None
        user_id = session_resp.data[0]["user_id"]
        user_resp = self.client.table("users").select("id, username, role, sector").eq("id", user_id).execute()
        if not user_resp.data:
            return None
        row = user_resp.data[0]
        return {"id": row["id"], "username": row["username"], "role": row["role"], "sector": row.get("sector") or ""}

    def delete_session(self, token: str):
        self.client.table("sessions").delete().eq("token", token).execute()

    # ── Users ─────────────────────────────────────────────────────────────

    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            response = self.client.table("users").insert({
                "username": username,
                "password_hash": pw,
                "role": role,
                "sector": "",
            }).execute()
            return bool(response.data)
        except Exception:
            return False

    def change_password(self, user_id: int, new_password: str):
        pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.client.table("users").update({"password_hash": pw}).eq("id", user_id).execute()

    def delete_user(self, user_id: int):
        self.client.table("users").delete().eq("id", user_id).neq("role", "admin").execute()

    def list_users(self) -> list[dict]:
        response = self.client.table("users").select("id, username, role, sector, created_at").order("role", desc=True).order("username").execute()
        return response.data or []

    def set_user_sector(self, user_id: int, sector: str):
        self.client.table("users").update({"sector": sector}).eq("id", user_id).execute()

    # ── Access windows ────────────────────────────────────────────────────

    def add_access(self, user_id: int, start: date, end: date, sector: str, note: str = ""):
        self.client.table("access_windows").insert({
            "user_id": user_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "sector": sector,
            "note": note,
        }).execute()

    def list_access(self, user_id: int) -> list[dict]:
        response = (
            self.client.table("access_windows")
            .select("id, start_date, end_date, sector, note")
            .eq("user_id", user_id)
            .order("start_date", desc=True)
            .execute()
        )
        return response.data or []

    def delete_access(self, window_id: int):
        self.client.table("access_windows").delete().eq("id", window_id).execute()

    def cleanup_expired_access(self):
        today = date.today().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        self.client.table("access_windows").delete().lt("end_date", today).execute()
        self.client.table("sessions").delete().lt("expires_at", now).execute()

    def get_today_access(self, user_id: int) -> tuple[bool, str]:
        today = date.today().isoformat()
        response = (
            self.client.table("access_windows")
            .select("sector")
            .eq("user_id", user_id)
            .lte("start_date", today)
            .gte("end_date", today)
            .limit(1)
            .execute()
        )
        if response.data:
            return True, response.data[0].get("sector") or ""
        return False, ""
