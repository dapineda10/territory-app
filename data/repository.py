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
        return {row["zona"]: row["estado"] for row in (response.data or [])}
