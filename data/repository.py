from datetime import datetime, timezone
from typing import Dict
from supabase import Client


class EstadoRepository:
    def __init__(self, client: Client):
        self.client = client

    def guardar(self, zona: str, estado: str):
        self.client.table("progreso").upsert({
            "zona": zona,
            "estado": estado,
            "fecha": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="zona").execute()

    def obtener_estados(self) -> Dict[str, str]:
        response = self.client.table("progreso").select("zona, estado").execute()
        return {
            row["zona"]: row["estado"]
            for row in (response.data or [])
            if not row["zona"].startswith("__")
        }

    def guardar_siguiente(self, sector: str, zona_id: str | None):
        key = f"__siguiente:{sector}"
        if zona_id:
            self.client.table("progreso").upsert({
                "zona": key,
                "estado": zona_id,
                "fecha": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="zona").execute()
        else:
            self.client.table("progreso").delete().eq("zona", key).execute()

    def obtener_todos_siguientes(self) -> Dict[str, str]:
        response = self.client.table("progreso").select("zona, estado").execute()
        result = {}
        for row in (response.data or []):
            key = row["zona"]
            if key.startswith("__siguiente:"):
                sector = key[len("__siguiente:"):]
                result[sector] = row["estado"]
        return result
