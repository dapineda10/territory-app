import json
import os
from datetime import datetime
from typing import Dict, List

class EstadoRepository:

    def __init__(self, path: str = "data/progreso.json"):
        self.path = path

    def _leer(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

    def guardar(self, zona: str, estado: str):
        data = self._leer()

        data.append({
            "zona": zona,
            "estado": estado,
            "fecha": datetime.now().isoformat()
        })

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def obtener_estados(self) -> Dict[str, str]:
        data = self._leer()

        estados = {}
        for item in data:
            estados[item["zona"]] = item["estado"]

        return estados