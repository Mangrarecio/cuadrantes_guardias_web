# -*- coding: utf-8 -*-
"""
Cuadrantes de guardias 2027-2030 · MODO CONSULTA
Versión para publicar en Internet (Streamlit Community Cloud) y compartir con los compañeros.
Muestra solo el cuadrante aprobado: no hay barra lateral ni buscador y nadie puede cambiar la
configuración. La combinación aprobada es motor.CONFIG_RECOMENDADA.
"""
import datetime as dt
import json

import pandas as pd
import streamlit as st

import exportar
import motor

st.set_page_config(page_title="Cuadrantes de guardias 2027-2030", page_icon="📅",
                   layout="wide", initial_sidebar_state="collapsed")

# Oculta por completo la barra lateral (modo consulta)
st.markdown(
    "<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'], "
    "[data-testid='collapsedControl'] {display: none;}</style>",
    unsafe_allow_html=True,
)

LETRAS = motor.TRABAJADORES
COLORES = {"A": "#BDD7EE", "B": "#C6E0B4", "C": "#FFE699", "D": "#F8CBAD"}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CFG = motor.CONFIG_RECOMENDADA          # combinación aprobada (fija)


def mapear(styler, func, subset=None):
    metodo = styler.map if hasattr(styler, "map") else styler.applymap
    return metodo(func, subset=subset)


def colorear(v):
    if not isinstance(v, str) or not v:
        return "background-color: #d9d9d9"
    estilo = f"background-color: {COLORES.get(v[0], '#ffffff')}; color: #000000; text-align: center;"
    if "★" in v:
        estilo += " font-weight: 700; border: 2px solid #c00000;"
    return estilo


@st.cache_data(show_spinner=False)
def calcular():
    res, bloques, vac = motor.generar(CFG)
    aud = motor.auditar(bloques, res, vac)
    return res, bloques, vac, aud


@st.cache_data(show_spinner=False)
def libro(anios):
    res, bloques, vac, aud = calcular()
    return exportar.crear_libro(res, bloques, aud, list(anios))


res, bloques, vac, aud = calcular()

st.title("📅 Cuadrantes de guardias 2027-2030")
st.caption("4 trabajadores (A, B, C, D) · guardias de 24 h · del 01/01/2027 al 31/12/2030")
if all(a["ok"] for a in aud):
    st.success("✅ Cuadrante verificado: cumple todas las condiciones establecidas.")
else:
    st.error("❌ Hay condiciones que no se cumplen. Avisa a quien administra la aplicación.")

tab_cuad, tab_vac, tab_fest, tab_exp = st.tabs(
    ["📅 Cuadrante", "🏖️ Vacaciones", "🎄 Festivos", "📥 Descargar Excel"])

# ----------------------------------------------------------------------------- cuadrante
with tab_cuad:
    c1, c2 = st.columns([1, 2])
    anio = c1.selectbox("Año", motor.ANIOS)
    vista = c2.radio("Vista", ["Anual (días × meses)", "Mensual (detalle)"], horizontal=True)
    por_anio = motor.guardias_por_anio(res)[anio]
    cols = st.columns(4)
    for w, L in enumerate(LETRAS):
        cols[w].metric(f"Guardias de {L} en {anio}", por_anio[w])

    if vista.startswith("Anual"):
        letras, fest = motor.matriz_anual(res, anio)
        datos = [[(letras[d][m] + ("★" if fest[d][m] else "")) if letras[d][m] else ""
                  for m in range(12)] for d in range(31)]
        df = pd.DataFrame(datos, index=range(1, 32), columns=[m.capitalize() for m in motor.MESES])
        df.index.name = "Día"
        st.dataframe(mapear(df.style, colorear), height=1130)
        st.caption("★ = día señalado que rota (24, 25 y 31 dic, 1 ene, Jueves y Viernes Santo).")
        cuenta = motor.guardias_por_mes(res, anio)
        dfm = pd.DataFrame(cuenta, index=[m.capitalize() for m in motor.MESES]).T
        dfm["Total"] = dfm.sum(axis=1)
        st.markdown("**Guardias por mes**")
        st.dataframe(dfm)
    else:
        mes = st.selectbox("Mes", list(range(1, 13)),
                           format_func=lambda m: motor.MESES_LARGOS[m - 1].capitalize())
        nombres_fest = {f: n for y in motor.ANIOS for n, f in motor.festivos(y).items()}
        filas = []
        d = dt.date(anio, mes, 1)
        while d.month == mes:
            i = (d - motor.FECHA_INICIO).days
            if 0 <= i < motor.N_DIAS:
                filas.append({
                    "Fecha": d.strftime("%d/%m/%Y"),
                    "Día": motor.DIAS_SEMANA[d.weekday()],
                    "Trabaja": LETRAS[res[i]],
                    "De vacaciones": ", ".join(LETRAS[w] for w in vac[i]) or "—",
                    "Día señalado": nombres_fest.get(d, ""),
                })
            d += dt.timedelta(days=1)
        dfd = pd.DataFrame(filas)
        st.dataframe(mapear(dfd.style, colorear, subset=["Trabaja"]), hide_index=True, height=1130)

# ----------------------------------------------------------------------------- vacaciones
with tab_vac:
    st.markdown("**Tramos de vacaciones por año** (cada año cada trabajador pasa al tramo siguiente)")
    for tipo, icono in (("Verano", "☀️"), ("Invierno", "❄️")):
        filas = []
        for y in motor.ANIOS:
            fila = {"Año": y}
            for w, L in enumerate(LETRAS):
                tr = [f"{b['inicio']:%d/%m}–{b['fin']:%d/%m}" for b in bloques
                      if b["trabajador"] == w and b["tipo"] == tipo and b["inicio"].year == y]
                fila[L] = " y ".join(tr) if tr else "—"
            filas.append(fila)
        st.markdown(f"{icono} **{tipo}**")
        st.dataframe(pd.DataFrame(filas), hide_index=True)

    st.markdown("**Listado completo**")
    filtro = st.selectbox("Filtrar por año", ["Todos"] + motor.ANIOS)
    filas = []
    for b in sorted(bloques, key=lambda b: (b["inicio"], b["trabajador"])):
        filas.append({
            "Año": b["inicio"].year, "Trabajador": LETRAS[b["trabajador"]], "Tipo": b["tipo"],
            "Inicio": b["inicio"].strftime("%d/%m/%Y"), "Fin": b["fin"].strftime("%d/%m/%Y"),
            "Días": (min(b["fin"], motor.FECHA_FIN) - max(b["inicio"], motor.FECHA_INICIO)).days + 1,
        })
    dfv = pd.DataFrame(filas)
    if filtro != "Todos":
        dfv = dfv[dfv["Año"] == filtro]
    st.dataframe(mapear(dfv.style, colorear, subset=["Trabajador"]), hide_index=True)

# ----------------------------------------------------------------------------- festivos
with tab_fest:
    st.markdown("**Quién trabaja cada día señalado** (rota entre los 4 trabajadores)")
    filas = []
    for nombre in motor.NOMBRES_FESTIVOS:
        fila = {"Día señalado": nombre}
        for y in motor.ANIOS:
            f = motor.festivos(y)[nombre]
            w = res[(f - motor.FECHA_INICIO).days]
            fila[str(y)] = f"{LETRAS[w]} · {f:%d/%m}"
        filas.append(fila)
    dff = pd.DataFrame(filas)
    st.dataframe(mapear(dff.style, colorear, subset=[str(y) for y in motor.ANIOS]), hide_index=True)

# ----------------------------------------------------------------------------- excel
with tab_exp:
    st.markdown("Descarga el cuadrante en Excel: una hoja por año (días × meses con colores), "
                "más las hojas de vacaciones, festivos, resumen y auditoría.")
    st.download_button("⬇️ Excel completo 2027-2030", data=libro(tuple(motor.ANIOS)),
                       file_name="cuadrante_2027-2030.xlsx", mime=XLSX)
    st.markdown("**Un año por archivo**")
    cols = st.columns(4)
    for j, y in enumerate(motor.ANIOS):
        cols[j].download_button(f"⬇️ Año {y}", data=libro((y,)),
                                file_name=f"cuadrante_{y}.xlsx", mime=XLSX, key=f"dl_{y}")
