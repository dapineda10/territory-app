import streamlit as st
import folium
from streamlit_folium import st_folium
from services.geo_service import cargar_geometrias
from data.repository import EstadoRepository
from data.auth_repository import AuthRepository
from data.supabase_client import get_supabase
from folium.features import DivIcon
from datetime import date
import os
import json
import colorsys
import hashlib
import math

st.set_page_config(
    layout="wide",
    page_title="Predicación Bosques del Norte",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
#MainMenu, footer { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container {
    padding: 0.5rem 0.75rem 0.5rem !important;
    max-width: 100% !important;
}
h1 { margin: 0 0 0.4rem !important; font-size: 1.2rem !important; }
[data-testid="stProgressBar"] > div { font-size: 0.78rem; }
@media (max-width: 768px) {
    .block-container { padding: 0.25rem 0.4rem 0 !important; }
    h1 { font-size: 1rem !important; }
    iframe { height: 62vh !important; min-height: 320px; }
    .stButton > button { min-height: 2.8rem !important; font-size: 1rem !important; }
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# CACHE
# =============================================================================

@st.cache_resource
def get_auth_repo():
    return AuthRepository(get_supabase())


@st.cache_resource
def inicializar_datos():
    repo = EstadoRepository(get_supabase())
    ruta = os.path.join("data", "zonas_manizales.geojson")
    padres, hijos = cargar_geometrias(ruta)
    return repo, padres, hijos


# =============================================================================
# HELPERS
# =============================================================================

def get_apple_svg(color_principal, color_oscuro, label=""):
    if label:
        char_count = len(str(label))
        rect_w = 8 + char_count * 5.5
        rect_x = 20 - rect_w / 2
        label_el = (
            f'<rect x="{rect_x:.1f}" y="17" width="{rect_w:.1f}" height="10" rx="3" ry="3" fill="white" fill-opacity="0.85"/>'
            f'<text x="20" y="25.5" text-anchor="middle" font-size="9.5" font-weight="bold" font-family="Arial,sans-serif" fill="#111">{label}</text>'
        )
    else:
        label_el = ""
    return f"""
    <svg width="44px" height="44px" viewBox="-1 -1 42.96 42.96" xmlns="http://www.w3.org/2000/svg">
        <path d="M14.384 11.484c-2.686 0.285 -4.759 2.983 -5.574 4.623 -3.764 7.58 5.965 19.618 9.497 18.815 0.539 -0.122 1.097 -0.571 2.329 -0.687 1.711 -0.161 2.629 0.52 3.662 0.639 2.25 0.26 4.285 -2.24 5.71 -3.99 1.608 -1.975 6.286 -7.719 4.507 -13.864 -0.289 -0.997 -1.026 -3.542 -3.423 -4.937 -0.155 -0.091 -2.989 -1.687 -5.649 -0.689 -1.006 0.377 -1.379 0.901 -2.629 1.088 -1.152 0.172 -1.986 -0.091 -2.901 -0.317 -1.482 -0.363 -4.055 -0.836 -5.529 -0.68z"
              fill="{color_principal}" stroke="#000" stroke-width="0.8"/>
        <path d="M30.072 25.371c-0.733 3.297 -3.716 6.954 -6.549 7.077 -1.046 0.045 -1.718 -0.408 -3.22 -0.069 -1.998 0.449 -3.743 1.908 -3.546 2.461 0.136 0.377 1.168 0.324 1.269 0.317 1.159 -0.068 1.458 -0.816 2.363 -0.922 1.027 -0.12 1.464 0.749 2.473 1.088 1.709 0.574 3.633 -0.855 4.707 -1.653 3.762 -2.794 8.822 -10.056 6.812 -17.131 -0.354 -1.244 -1.002 -3.406 -3.08 -4.747 -1.756 -1.133 -4.617 -1.729 -5.578 -0.634 -1.792 2.037 5.827 7.573 4.351 14.214"
              fill="{color_oscuro}" stroke="#000" stroke-width="0.5"/>
        {label_el}
    </svg>"""


def get_next_svg():
    return """<svg width="30px" height="46px" viewBox="0 0 30 46" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="15" cy="44" rx="7" ry="2" fill="rgba(0,0,0,0.25)"/>
        <path d="M12,0 L18,0 L18,26 L25,26 L15,43 L5,26 L12,26 Z"
              fill="#FFD700" stroke="#B8860B" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>"""


def color_from_name(name):
    return f"#{hashlib.md5(name.encode()).hexdigest()[:6]}"


def lighten_color(hex_color, amount=0.5):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = min(1, l + amount * (1 - l))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(int(r2*255), int(g2*255), int(b2*255))


# =============================================================================
# DIALOG
# =============================================================================

@st.dialog("🔄 Reset de sector")
def dialogo_reset(sector_name, hijos_vis, repo):
    st.markdown(f"¿Seguro que quieres poner el sector **{sector_name}** en pendiente?")
    st.markdown("Esta acción no se puede deshacer.")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✅ Sí, resetear", type="primary", use_container_width=True):
            for h in hijos_vis:
                repo.guardar(str(h["id"]), "pendiente")
            st.session_state["_force_estado_reload"] = True
            st.toast(f"El sector {sector_name} fue puesto en pendiente.")
            st.rerun()
    with col_no:
        if st.button("✖ Cancelar", use_container_width=True):
            st.rerun()


@st.dialog("🍏 Cambiar estado")
def dialogo_toggle(sector_id, estado_actual, repo, sector, es_siguiente=False):
    nuevo_estado = "completado" if estado_actual == "pendiente" else "pendiente"
    color = "green" if estado_actual == "completado" else "red"
    st.markdown(f"**Manzana {sector_id}**")
    st.markdown(f"Estado actual: :{color}[**{estado_actual.upper()}**]")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"✅ {nuevo_estado.upper()}", type="primary", use_container_width=True):
            repo.guardar(sector_id, nuevo_estado)
            st.session_state["_force_estado_reload"] = True
            st.session_state["_dismissed_popup"] = sector_id
            del st.session_state["confirmar_sector_id"]
            st.rerun()
    with col2:
        if st.button("✖ Cancelar", use_container_width=True):
            st.session_state["_dismissed_popup"] = sector_id
            del st.session_state["confirmar_sector_id"]
            st.rerun()
    st.markdown("---")
    if es_siguiente:
        if st.button("🗑 Quitar indicador ▼", use_container_width=True):
            repo.guardar_siguiente(sector, None)
            st.session_state["_dismissed_popup"] = sector_id
            del st.session_state["confirmar_sector_id"]
            st.rerun()
    else:
        if st.button("📍 Marcar como siguiente ▼", use_container_width=True):
            repo.guardar_siguiente(sector, sector_id)
            st.session_state["_dismissed_popup"] = sector_id
            del st.session_state["confirmar_sector_id"]
            st.rerun()


# =============================================================================
# MAP FRAGMENT
# =============================================================================

@st.fragment
def mostrar_mapa(can_edit: bool, user_sector: str = ""):
    repo, padres, hijos = inicializar_datos()
    estados = repo.obtener_estados()
    siguientes = repo.obtener_todos_siguientes()
    if "_force_estado_reload" in st.session_state:
        del st.session_state["_force_estado_reload"]

    # Sector types
    sector_set = set()
    for p in padres:
        s = p.get("sector_type", "")
        if s:
            sector_set.add(s)
    for h in hijos:
        s = h.get("sector", "")
        if s:
            sector_set.add(s)
    all_sectors = sorted({str(s) for s in sector_set}, key=str)
    ALL_KEY = "__all__"

    def sector_label(key):
        if key == ALL_KEY:
            return "Todos los sectores"
        return str(key).replace("_", " ").title()

    is_admin = st.session_state.get("user", {}).get("role") == "admin"

    if is_admin:
        selected_sector = st.selectbox(
            "Sector",
            [ALL_KEY] + all_sectors,
            format_func=sector_label,
            key="sector_selector",
            label_visibility="collapsed",
        )
    else:
        if not user_sector or user_sector not in all_sectors:
            st.error("No tienes acceso a ningún sector para hoy. Contacta al administrador.")
            return
        selected_sector = user_sector
        st.caption(f"📍 {sector_label(selected_sector)}")

    sector_changed = st.session_state.get("_prev_sector") != selected_sector
    if sector_changed:
        st.session_state["_prev_sector"] = selected_sector

    if selected_sector == ALL_KEY:
        hijos_vis = hijos
        padres_vis = padres
    else:
        hijos_vis = [h for h in hijos if str(h.get("sector", "")) == selected_sector]
        padres_vis = [p for p in padres if str(p.get("sector_type", "")) == selected_sector]

    total = len(hijos_vis)
    completadas = sum(1 for h in hijos_vis if estados.get(str(h.get("id"))) == "completado")
    porcentaje = completadas / total if total > 0 else 0
    st.progress(porcentaje, text=f"{sector_label(selected_sector)}: {completadas}/{total} ({porcentaje*100:.1f}%)")

    if not can_edit:
        st.info("🔒 Solo visualización — sin acceso de edición para hoy.", icon="🔒")

    if "map_center" not in st.session_state or sector_changed:
        all_coords = [c for p in padres_vis for c in p["coords"]]
        all_coords += [h["coords"][0] for h in hijos_vis]
        if all_coords:
            lats = [c[0] for c in all_coords]
            lons = [c[1] for c in all_coords]
            span = max(max(lats) - min(lats), max(lons) - min(lons))
            st.session_state["map_center"] = [(min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2]
            st.session_state["map_zoom"] = max(12, min(int(math.log2(1125 / max(span, 0.001))), 18))

    center = st.session_state.get("map_center", [5.086, -75.488])
    zoom = st.session_state.get("map_zoom", 17)
    m = folium.Map(location=center, zoom_start=zoom, max_zoom=22, tiles=None, prefer_canvas=True)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="© Esri",
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)

    ruta_puntos = os.path.join("data", "puntos_referencia.json")
    if os.path.exists(ruta_puntos):
        with open(ruta_puntos, "r", encoding="utf-8") as f:
            puntos = json.load(f)
        for punto in puntos:
            folium.Marker(
                location=[punto["lat"], punto["lon"]],
                popup=punto["nombre"],
                icon=folium.Icon(color=punto.get("color", "blue"), icon=punto.get("icon", "info-sign")),
            ).add_to(m)

    categoria_por_padre = []
    for p in padres_vis:
        nombre = p.get("nombre", "Zona General")
        base = nombre.split()[0].lower() if nombre.split() else nombre.lower()
        categoria_por_padre.append(base)
    color_por_categoria = {cat: color_from_name(cat) for cat in set(categoria_por_padre)}

    for p, cat in zip(padres_vis, categoria_por_padre):
        color_linea = color_por_categoria[cat]
        color_relleno = lighten_color(color_linea, 0.5)
        coords = p["coords"]
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        folium.Polygon(
            locations=coords,
            color=color_linea,
            fill=True,
            fill_color=color_relleno,
            fill_opacity=0.4,
            weight=3,
        ).add_to(m)

    for hijo in hijos_vis:
        sector_id = str(hijo.get("id")) if hijo.get("id") is not None else None
        if not sector_id:
            continue
        estado = estados.get(sector_id, "pendiente")
        color1, color2 = ("#28a745", "#1e7e34") if estado == "completado" else ("#FA1919", "#C40000")
        label = str(hijo["codigo_manzana"]) if hijo.get("codigo_manzana") is not None else ""
        svg = get_apple_svg(color1, color2, label)
        folium.Marker(
            location=hijo["coords"][0],
            popup=folium.Popup(str(sector_id), max_width=200),
            icon=DivIcon(
                html=f'<div id="{sector_id}" style="cursor:pointer;filter:drop-shadow(0px 3px 3px rgba(0,0,0,0.4));">{svg}</div>',
                icon_anchor=(22, 22),
            ),
        ).add_to(m)

    for hijo in hijos_vis:
        hijo_sector = str(hijo.get("sector", ""))
        if siguientes.get(hijo_sector) == str(hijo.get("id")):
            folium.Marker(
                location=hijo["coords"][0],
                icon=DivIcon(
                    html=f'<div style="pointer-events:none;filter:drop-shadow(0px 2px 5px rgba(0,0,0,0.5));">{get_next_svg()}</div>',
                    icon_anchor=(15, 43),
                ),
            ).add_to(m)

    output = st_folium(
        m,
        key="mapa_manizales",
        height=680,
        use_container_width=True,
        returned_objects=["last_object_clicked_popup"],
    )

    if output and output.get("last_object_clicked_popup"):
        sector_id = str(output["last_object_clicked_popup"])
        dismissed = st.session_state.get("_dismissed_popup", "")
        if sector_id != dismissed and any(str(h.get("id")) == sector_id for h in hijos_vis):
            st.session_state.pop("_dismissed_popup", None)
            if can_edit:
                st.session_state["confirmar_sector_id"] = sector_id
            else:
                st.toast("🔒 Sin acceso de edición para hoy.", icon="🔒")

    sector_id = st.session_state.get("confirmar_sector_id")
    if sector_id and any(str(h.get("id")) == sector_id for h in hijos_vis):
        hijo_sector = next((str(h.get("sector", "")) for h in hijos_vis if str(h.get("id")) == sector_id), "")
        dialogo_toggle(sector_id, estados.get(sector_id, "pendiente"), repo, hijo_sector, es_siguiente=(siguientes.get(hijo_sector) == sector_id))

    if st.session_state.get("user", {}).get("role") == "admin" and selected_sector != ALL_KEY:
        st.markdown("---")
        if st.button("🔄 Reset: poner todo PENDIENTE", type="secondary"):
            dialogo_reset(sector_label(selected_sector), hijos_vis, repo)


# =============================================================================
# ADMIN PANEL PAGE
# =============================================================================

def pagina_admin():
    auth_repo = get_auth_repo()
    auth_repo.cleanup_expired_access()

    _, padres, hijos = inicializar_datos()
    sector_set = set()
    for p in padres:
        s = p.get("sector_type", "")
        if s:
            sector_set.add(str(s))
    for h in hijos:
        s = h.get("sector", "")
        if s:
            sector_set.add(str(s))
    all_sectors = sorted(sector_set, key=str)

    st.subheader("⚙️ Administración")
    tab_users, tab_access = st.tabs(["👥 Usuarios", "📅 Acceso"])

    with tab_users:
        users = auth_repo.list_users()

        for u in users:
            is_admin = u["role"] == "admin"
            icon = "👑" if is_admin else "👤"
            with st.container(border=True):
                col_name, col_del = st.columns([3, 1])
                with col_name:
                    st.markdown(f"**{icon} {u['username']}**")
                with col_del:
                    if not is_admin:
                        if st.button("🗑", key=f"del_user_{u['id']}", help="Eliminar usuario"):
                            auth_repo.delete_user(u["id"])
                            st.rerun()

                with st.popover("🔑 Cambiar contraseña", use_container_width=True):
                    new_pw = st.text_input("Nueva contraseña", type="password", key=f"pw_{u['id']}")
                    if st.button("Guardar", key=f"save_pw_{u['id']}"):
                        if len(new_pw) >= 6:
                            auth_repo.change_password(u["id"], new_pw)
                            st.success("Contraseña actualizada.")
                        else:
                            st.error("Mínimo 6 caracteres.")

        st.markdown("---")
        st.markdown("**Nuevo usuario**")
        with st.form("form_nuevo_usuario", clear_on_submit=True):
            new_username = st.text_input("Usuario")
            new_password = st.text_input("Contraseña", type="password")
            new_role = st.selectbox("Rol", ["user", "admin"])
            if st.form_submit_button("Crear usuario", use_container_width=True):
                if not new_username or not new_password:
                    st.error("Usuario y contraseña son requeridos.")
                elif len(new_password) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                else:
                    ok = auth_repo.create_user(new_username, new_password, new_role)
                    if ok:
                        st.success(f"Usuario **{new_username}** creado.")
                        st.rerun()
                    else:
                        st.error("El nombre de usuario ya existe.")

    with tab_access:
        users = auth_repo.list_users()
        non_admins = [u for u in users if u["role"] != "admin"]
        if not non_admins:
            st.info("No hay usuarios regulares todavía.")
        else:
            selected_user = st.selectbox(
                "Usuario",
                non_admins,
                format_func=lambda u: u["username"],
                key="admin_access_user",
            )
            uid = selected_user["id"]

            windows = auth_repo.list_access(uid)
            if windows:
                st.markdown("**Accesos activos:**")
                today_str = date.today().isoformat()
                for w in windows:
                    col_w, col_wdel = st.columns([4, 1])
                    with col_w:
                        sector_w = str(w.get("sector") or "").replace("_", " ").title() or "—"
                        note = f" — {w['note']}" if w.get("note") else ""
                        active = w["start_date"] <= today_str <= w["end_date"]
                        status = "🟢" if active else "🔵"
                        st.markdown(f"{status} **{sector_w}** · `{w['start_date']}` → `{w['end_date']}`{note}")
                    with col_wdel:
                        if st.button("🗑", key=f"del_win_{w['id']}"):
                            auth_repo.delete_access(w["id"])
                            st.rerun()
            else:
                st.info("Sin accesos asignados.")

            st.markdown("---")
            st.markdown("**Asignar nuevo acceso**")
            with st.form("form_acceso", clear_on_submit=True):
                today = date.today()
                sector_input = st.selectbox(
                    "Sector",
                    all_sectors,
                    format_func=lambda s: str(s).replace("_", " ").title(),
                    key="access_sector",
                )
                date_range = st.date_input(
                    "Rango de fechas",
                    value=(today, today),
                    min_value=date(2024, 1, 1),
                    key="access_dates",
                )
                note_input = st.text_input("Nota (opcional)")
                if st.form_submit_button("Asignar acceso", use_container_width=True):
                    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                        auth_repo.add_access(uid, date_range[0], date_range[1], str(sector_input), note_input)
                        st.success(f"Acceso asignado a **{selected_user['username']}**.")
                        st.rerun()
                    else:
                        st.error("Selecciona un rango de fechas válido.")


# =============================================================================
# LOGIN PAGE
# =============================================================================

def pagina_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col_c = st.columns([1, 2, 1])[1]
    with col_c:
        st.title("📍 Predicación Bosques del Norte")
        st.markdown("---")
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="tu usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••")
            submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")
        if submitted:
            auth_repo = get_auth_repo()
            user = auth_repo.verify(username, password)
            if user:
                token = auth_repo.create_session(user["id"])
                st.session_state["user"] = user
                st.session_state["session_token"] = token
                st.query_params["s"] = token
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")


# =============================================================================
# ENTRY
# =============================================================================

def main():
    auth_repo = get_auth_repo()

    # Restore session from persistent token in URL
    user = st.session_state.get("user")
    if not user:
        token = st.query_params.get("s")
        if token:
            user = auth_repo.validate_session(token)
            if user:
                st.session_state["user"] = user
                st.session_state["session_token"] = token

    if not user:
        pagina_login()
        return

    is_admin = user["role"] == "admin"
    if is_admin:
        can_edit = True
        user_sector = ""
    else:
        can_edit, user_sector = auth_repo.get_today_access(user["id"])

    # Top bar
    col_title, col_info, col_out = st.columns([5, 3, 1])
    with col_title:
        st.title("📍 Predicación Bosques del Norte")
    with col_info:
        role_icon = "👑" if is_admin else "👤"
        if not is_admin:
            edit_label = "✏️ editar" if can_edit else "👁 solo ver"
            st.caption(f"{role_icon} {user['username']}  ·  {edit_label}")
        else:
            st.caption(f"{role_icon} {user['username']}  ·  Admin")
    with col_out:
        if st.button("Salir", use_container_width=True):
            token = st.session_state.pop("session_token", None)
            if token:
                auth_repo.delete_session(token)
            st.session_state.pop("user", None)
            st.query_params.clear()
            st.rerun()

    # Page navigation (admin only)
    if is_admin:
        page = st.selectbox(
            "Ir a",
            ["🗺️ Mapa", "⚙️ Administración"],
            key="page_nav",
            label_visibility="collapsed",
        )
    else:
        page = "🗺️ Mapa"

    if page == "🗺️ Mapa":
        mostrar_mapa(can_edit, user_sector)
    else:
        pagina_admin()


if __name__ == "__main__":
    main()
