import json
import streamlit as st
from shapely.geometry import shape, Polygon, LineString
from shapely.geometry.base import BaseGeometry
from typing import List, Dict, Any


# -----------------------------
# convertir a polígono si es posible
# -----------------------------
def normalizar_geometria(geom: BaseGeometry) -> BaseGeometry | None:

    if geom.is_empty:
        return None

    # si ya es polígono
    if geom.geom_type in ["Polygon", "MultiPolygon"]:
        return geom

    # si es LineString cerrada → Polygon
    if geom.geom_type == "LineString":
        coords = list(geom.coords)

        if coords[0] == coords[-1] and len(coords) >= 4:
            return Polygon(coords)

        # si no está cerrada, cerrarla manualmente
        coords.append(coords[0])
        return Polygon(coords)

    return None


# -----------------------------
# coords seguras para folium
# -----------------------------
def extraer_coords(geom: BaseGeometry) -> List[List[float]]:

    if geom.geom_type == "Polygon":
        return [[lat, lon] for lon, lat in geom.exterior.coords]

    if geom.geom_type == "MultiPolygon":
        poly = max(geom.geoms, key=lambda g: g.area)
        return [[lat, lon] for lon, lat in poly.exterior.coords]

    return []


# -----------------------------
# loader principal
# -----------------------------
@st.cache_resource
def cargar_geometrias(ruta_archivo):
    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    padres = []
    hijos = []
    
    for feature in data['features']:
        geom = feature['geometry']
        tipo_geo = geom['type']
        props = feature.get("properties", {})

        # --- Extracción dinámica del nombre del sector ---
        nombre_sector = "Zona General"
        for k, v in props.items():
            if v != "" and v is not None:
                nombre_sector = f"{k.strip().title()} {v}"
                break

        # --- Procesamiento de Coordenadas ---
        if tipo_geo == "Polygon":
            # Solo agregar hijos si tienen codigo_manzana válido
            if "codigo_manzana" in props and props["codigo_manzana"] not in (None, ""):
                coords_raw = geom['coordinates'][0]
                coords_listas = [[p[1], p[0]] for p in coords_raw]
                hijo = {"nombre": nombre_sector, "coords": coords_listas, "id": str(props["codigo_manzana"])}
                hijos.append(hijo)
        elif tipo_geo == "LineString":
            coords_raw = geom['coordinates']
            coords_listas = [[p[1], p[0]] for p in coords_raw]
            padre = {"nombre": nombre_sector, "coords": coords_listas}
            padres.append(padre)
    return padres, hijos