import streamlit as st
import folium
from streamlit_folium import st_folium
from services.geo_service import cargar_geometrias
from data.repository import EstadoRepository
from folium.features import DivIcon
import os
import uuid
import json

st.set_page_config(layout="wide", page_title="Control Territorial Manizales")


# =========================
# DATOS
# =========================
@st.cache_resource
def inicializar_datos():
    repo = EstadoRepository()
    ruta_geojson = os.path.join("data", "zonas_manizales.geojson")
    padres, hijos = cargar_geometrias(ruta_geojson)

    # 🔥 ASIGNAR ID ÚNICO SOLO SI NO HAY codigo_manzana
    for i, h in enumerate(hijos):
        if "id" not in h or not h["id"]:
            h["id"] = str(i)

    return repo, padres, hijos


# =========================
# SVG
# =========================
def get_apple_svg(color_principal, color_oscuro):
    return f"""
    <svg width="36px" height="36px" viewBox="-1 -1 42.96 42.96" xmlns="http://www.w3.org/2000/svg">
        <path d="M14.384 11.484c-2.686 0.285 -4.759 2.983 -5.574 4.623 -3.764 7.58 5.965 19.618 9.497 18.815 0.539 -0.122 1.097 -0.571 2.329 -0.687 1.711 -0.161 2.629 0.52 3.662 0.639 2.25 0.26 4.285 -2.24 5.71 -3.99 1.608 -1.975 6.286 -7.719 4.507 -13.864 -0.289 -0.997 -1.026 -3.542 -3.423 -4.937 -0.155 -0.091 -2.989 -1.687 -5.649 -0.689 -1.006 0.377 -1.379 0.901 -2.629 1.088 -1.152 0.172 -1.986 -0.091 -2.901 -0.317 -1.482 -0.363 -4.055 -0.836 -5.529 -0.68z"
              fill="{color_principal}" stroke="#000" stroke-width="0.8"/>
        <path d="M30.072 25.371c-0.733 3.297 -3.716 6.954 -6.549 7.077 -1.046 0.045 -1.718 -0.408 -3.22 -0.069 -1.998 0.449 -3.743 1.908 -3.546 2.461 0.136 0.377 1.168 0.324 1.269 0.317 1.159 -0.068 1.458 -0.816 2.363 -0.922 1.027 -0.12 1.464 0.749 2.473 1.088 1.709 0.574 3.633 -0.855 4.707 -1.653 3.762 -2.794 8.822 -10.056 6.812 -17.131 -0.354 -1.244 -1.002 -3.406 -3.08 -4.747 -1.756 -1.133 -4.617 -1.729 -5.578 -0.634 -1.792 2.037 5.827 7.573 4.351 14.214"
              fill="{color_oscuro}" stroke="#000" stroke-width="0.5"/>
    </svg>
    """


# =========================
# MAPA
# =========================
@st.fragment
def mostrar_mapa():
    repo, padres, hijos = inicializar_datos()
    if "_force_estado_reload" in st.session_state:
        estados = repo.obtener_estados()
        del st.session_state["_force_estado_reload"]
    else:
        estados = repo.obtener_estados()

    # ------------------------- 
    # BARRA DE PROGRESO
    # -------------------------
    total_manzanas = len(hijos)
    completadas = 0
    for h in hijos:
        sid = str(h.get("id"))
        if estados.get(sid) == "completado":
            completadas += 1
    porcentaje = completadas / total_manzanas if total_manzanas > 0 else 0
    st.markdown(f"### Progreso de territorio predicado")
    st.progress(porcentaje, text=f"{porcentaje*100:.1f}% completado")
    # -------------------------
    # MAPA
    # -------------------------
    # Leer centro y zoom guardados en session_state
    default_location = [5.086, -75.488]
    # Asegurar que location sea siempre [lat, lng]
    raw_center = st.session_state.get("map_center", default_location)
    if isinstance(raw_center, dict) and "lat" in raw_center and "lng" in raw_center:
        location = [raw_center["lat"], raw_center["lng"]]
    else:
        location = raw_center
    zoom = st.session_state.get("map_zoom", 19)
    m = folium.Map(
        location=location,
        zoom_start=zoom,
        max_zoom=22,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
    )

    # -------------------------
    # PUNTOS DE REFERENCIA
    # -------------------------
    ruta_puntos = os.path.join("data", "puntos_referencia.json")
    if os.path.exists(ruta_puntos):
        with open(ruta_puntos, "r", encoding="utf-8") as f:
            puntos = json.load(f)
        for punto in puntos:
            folium.Marker(
                location=[punto["lat"], punto["lon"]],
                popup=punto["nombre"],
                icon=folium.Icon(color=punto.get("color", "blue"), icon=punto.get("icon", "info-sign"))
            ).add_to(m)

    repo, padres, hijos = inicializar_datos()
    # Si se acaba de actualizar un estado, forzar recarga de estados desde el repo
    if "_force_estado_reload" in st.session_state:
        estados = repo.obtener_estados()
        del st.session_state["_force_estado_reload"]
    else:
        estados = repo.obtener_estados()

    st.title("📍 Control Territorial - Manizales")
    contenedor_info = st.container()

    # -------------------------
    # POLYLINES (coloreadas por categoría)
    # -------------------------
    def color_from_name(name):
        # Genera un color hex a partir del nombre (hash simple)
        import hashlib
        h = hashlib.md5(name.encode()).hexdigest()
        return f"#{h[:6]}"

    # Extraer nombre base de categoría para cada padre
    categoria_por_padre = []
    for p in padres:
        # El nombre viene como 'San Sebastian 1', 'Melquisedec 2', etc.
        nombre = p.get("nombre", "Zona General")
        base = nombre.split()[0].lower() if len(nombre.split()) > 1 else nombre.lower()
        categoria_por_padre.append(base)

    # Asignar color único por categoría
    categorias = list(set(categoria_por_padre))
    color_por_categoria = {cat: color_from_name(cat) for cat in categorias}

    import colorsys
    def lighten_color(hex_color, amount=0.5):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
        l = min(1, l + amount * (1 - l))
        r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
        return '#{:02x}{:02x}{:02x}'.format(int(r2*255), int(g2*255), int(b2*255))

    for p, cat in zip(padres, categoria_por_padre):
        color_linea = color_por_categoria[cat]
        color_relleno = lighten_color(color_linea, 0.5)
        coords = p["coords"]
        # Si la línea no está cerrada, cerrarla para formar un polígono visual
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        folium.Polygon(
            locations=coords,
            color=color_linea,
            fill=True,
            fill_color=color_relleno,
            fill_opacity=0.4,
            weight=3,
            popup=folium.Popup(p.get("nombre", cat.title()), max_width=250),
            tooltip=cat.title()
        ).add_to(m)

    # -------------------------
    # MARKERS (CON ID FIJO, SIN TOOLTIP)
    # -------------------------
    for i, hijo in enumerate(hijos):
        nombre = hijo.get("nombre", f"Manzana_{i}")
        sector_id = str(hijo.get("id")) if hijo.get("id") is not None else None
        if not sector_id:
            # No tiene id, no es interactivo
            continue
        estado = estados.get(sector_id, "pendiente")
        if estado == "completado":
            color1 = "#28a745"
            color2 = "#1e7e34"
        else:
            color1 = "#FA1919"
            color2 = "#C40000"
        svg = get_apple_svg(color1, color2)
        folium.Marker(
            location=hijo["coords"][0],
            popup=folium.Popup(str(sector_id), max_width=200),
            icon=DivIcon(
                html=f"""
                <div id=\"{sector_id}\" style="
                    cursor:pointer;
                    filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.4));
                ">
                    {svg}
                </div>
                """,
                icon_anchor=(18, 18)
            )
        ).add_to(m)

    # -------------------------
    # CLICK STREAMLIT
    # -------------------------
    output = st_folium(
        m,
        key="mapa_manizales",
        height=600,
        use_container_width=True,
        returned_objects=["last_object_clicked_popup", "center", "zoom"]
    )

    # -------------------------
    # LOGICA DE CLICK (SOLO ID)
    # -------------------------
    # Al hacer click en el marker, cambiar el estado inmediatamente
    # Al hacer click en el marker, guardar el id en session_state para confirmar
    if output and output.get("last_object_clicked_popup"):
        sector_id = str(output["last_object_clicked_popup"])
        if any(str(h.get("id")) == sector_id for h in hijos):
            st.session_state["confirmar_sector_id"] = sector_id
        # Guardar centro y zoom actuales en session_state
        if output.get("center"):
            center_val = output["center"]
            if isinstance(center_val, dict) and "lat" in center_val and "lng" in center_val:
                st.session_state["map_center"] = [center_val["lat"], center_val["lng"]]
            else:
                st.session_state["map_center"] = center_val
        if output.get("zoom"):
            st.session_state["map_zoom"] = output["zoom"]

    # Si hay un id pendiente de confirmación, mostrar panel y botón
    sector_id = st.session_state.get("confirmar_sector_id")
    if sector_id and any(str(h.get("id")) == sector_id for h in hijos):
        estado_actual = estados.get(sector_id, "pendiente")
        nuevo_estado = "completado" if estado_actual == "pendiente" else "pendiente"
        with contenedor_info:
            st.markdown("---")
            st.subheader(f"🍏 {sector_id}")
            color = "green" if estado_actual == "completado" else "red"
            st.markdown(f"Estado actual: :{color}[**{estado_actual.upper()}**]")
            if st.button(f"Confirmar cambio a {nuevo_estado.upper()}", type="primary"):
                repo.guardar(sector_id, nuevo_estado)
                st.toast(f"✅ Estado de {sector_id} cambiado a {nuevo_estado}")
                st.session_state["_force_estado_reload"] = True
                st.session_state["_show_success"] = f"Estado de {sector_id} cambiado a {nuevo_estado.upper()}"
                del st.session_state["confirmar_sector_id"]
                st.rerun()
    # Mostrar confirmación visual si existe
    if st.session_state.get("_show_success"):
        st.success(st.session_state["_show_success"])
        del st.session_state["_show_success"]


    # -------------------------
    # BOTÓN DE RESET
    # -------------------------
    if st.button("🔄 Reset: poner todo PENDIENTE", type="secondary"):
        for h in hijos:
            repo.guardar(str(h["id"]), "pendiente")
        st.session_state["_force_estado_reload"] = True
        st.session_state["_show_success"] = "Todos los sectores fueron puestos en PENDIENTE."
        st.rerun()


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    mostrar_mapa()