# -*- coding: utf-8 -*-
"""
exportar.py
Genera el Excel del cuadrante (un libro con una hoja por año, vacaciones, festivos, resumen y auditoría).
"""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

import motor

COLOR = {"A": "BDD7EE", "B": "C6E0B4", "C": "FFE699", "D": "F8CBAD"}
_fino = Side(style="thin", color="999999")
_rojo = Side(style="medium", color="C00000")
BORDE = Border(left=_fino, right=_fino, top=_fino, bottom=_fino)
BORDE_FEST = Border(left=_rojo, right=_rojo, top=_rojo, bottom=_rojo)
CENTRO = Alignment(horizontal="center", vertical="center")


def _fill(hexa):
    return PatternFill("solid", start_color=hexa, end_color=hexa)


def _cabecera(ws, fila, valores, col_ini=1):
    for j, v in enumerate(valores):
        c = ws.cell(row=fila, column=col_ini + j, value=v)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = _fill("404040")
        c.alignment = CENTRO
        c.border = BORDE


def _anchos(ws, anchos):
    for i, a in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = a


def _vertical_a_pagina(ws):
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def _hoja_anual(wb, anio, res):
    ws = wb.create_sheet(f"Cuadrante {anio}")
    letras, fest = motor.matriz_anual(res, anio)
    ws["A1"] = f"Cuadrante de guardias {anio} · guardias de 24 h · trabajadores A, B, C y D"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:N1")

    _cabecera(ws, 3, ["Día"] + [m.capitalize() for m in motor.MESES])
    for d in range(31):
        fila = 4 + d
        c = ws.cell(row=fila, column=1, value=d + 1)
        c.font = Font(bold=True)
        c.alignment = CENTRO
        c.border = BORDE
        c.fill = _fill("F2F2F2")
        for m in range(12):
            v = letras[d][m]
            cel = ws.cell(row=fila, column=2 + m)
            cel.alignment = CENTRO
            if v:
                cel.value = v + ("*" if fest[d][m] else "")
                cel.fill = _fill(COLOR[v])
                if fest[d][m]:
                    cel.font = Font(bold=True, color="C00000")
                    cel.border = BORDE_FEST
                else:
                    cel.border = BORDE
            else:
                cel.fill = _fill("D9D9D9")
                cel.border = BORDE

    ws["A37"] = "Guardias por mes"
    ws["A37"].font = Font(bold=True, size=12)
    _cabecera(ws, 38, ["Trab."] + [m.capitalize() for m in motor.MESES] + ["Total"])
    cuenta = motor.guardias_por_mes(res, anio)
    for j, L in enumerate(motor.TRABAJADORES):
        fila = 39 + j
        c = ws.cell(row=fila, column=1, value=L)
        c.font = Font(bold=True)
        c.fill = _fill(COLOR[L])
        c.alignment = CENTRO
        c.border = BORDE
        for m in range(12):
            cel = ws.cell(row=fila, column=2 + m, value=cuenta[L][m])
            cel.alignment = CENTRO
            cel.border = BORDE
        cel = ws.cell(row=fila, column=14, value=sum(cuenta[L]))
        cel.alignment = CENTRO
        cel.font = Font(bold=True)
        cel.border = BORDE

    ws["A44"] = "Leyenda:"
    ws["A44"].font = Font(bold=True)
    for j, L in enumerate(motor.TRABAJADORES):
        c = ws.cell(row=44, column=2 + j, value=L)
        c.fill = _fill(COLOR[L])
        c.alignment = CENTRO
        c.font = Font(bold=True)
        c.border = BORDE
    ws["G44"] = "* = día señalado que rota entre los trabajadores (24, 25 y 31 dic, 1 ene, Jueves y Viernes Santo)"

    _anchos(ws, [9] + [7.5] * 12 + [8])
    ws.freeze_panes = "B4"
    _vertical_a_pagina(ws)


def _dias_en_rango(b):
    return (min(b["fin"], motor.FECHA_FIN) - max(b["inicio"], motor.FECHA_INICIO)).days + 1


def _hoja_vacaciones(wb, bloques, anios):
    ws = wb.create_sheet("Vacaciones")
    _cabecera(ws, 1, ["Periodo", "Tipo", "Trabajador", "Inicio", "Fin", "Días"])
    sel = [b for b in bloques if b["inicio"].year in anios or b["fin"].year in anios]
    for r, b in enumerate(sorted(sel, key=lambda b: (b["inicio"], b["trabajador"])), start=2):
        L = motor.TRABAJADORES[b["trabajador"]]
        vals = [b["periodo"], b["tipo"], L, b["inicio"], b["fin"], _dias_en_rango(b)]
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BORDE
            c.alignment = CENTRO
            if j in (4, 5):
                c.number_format = "DD/MM/YYYY"
            if j == 3:
                c.fill = _fill(COLOR[L])
                c.font = Font(bold=True)
    _anchos(ws, [12, 11, 12, 13, 13, 7])
    ws.freeze_panes = "A2"


def _hoja_festivos(wb, res, anios):
    ws = wb.create_sheet("Festivos")
    _cabecera(ws, 1, ["Día señalado"] + [str(y) for y in anios] + [f"Rotación {motor.ANIOS[0]}-{motor.ANIOS[-1]}"])
    for r, nombre in enumerate(motor.NOMBRES_FESTIVOS, start=2):
        c = ws.cell(row=r, column=1, value=nombre)
        c.font = Font(bold=True)
        c.border = BORDE
        for j, y in enumerate(anios, start=2):
            f = motor.festivos(y)[nombre]
            L = motor.TRABAJADORES[res[(f - motor.FECHA_INICIO).days]]
            cel = ws.cell(row=r, column=j, value=f"{L} · {f:%d/%m/%Y}")
            cel.fill = _fill(COLOR[L])
            cel.alignment = CENTRO
            cel.border = BORDE
        todos = {res[k] for k in motor._FEST_IDX[nombre]}
        cel = ws.cell(row=r, column=2 + len(anios), value="OK" if len(todos) == 4 else "REVISAR")
        cel.alignment = CENTRO
        cel.border = BORDE
        cel.font = Font(bold=True, color="2E7D32" if len(todos) == 4 else "C00000")
    _anchos(ws, [18] + [16] * len(anios) + [18])


def _hoja_resumen(wb, res, anios):
    ws = wb.create_sheet("Resumen")
    por_anio = motor.guardias_por_anio(res)
    _cabecera(ws, 1, ["Guardias"] + [str(y) for y in anios] + ["Total"])
    for w, L in enumerate(motor.TRABAJADORES):
        r = 2 + w
        c = ws.cell(row=r, column=1, value=f"Trabajador {L}")
        c.fill = _fill(COLOR[L])
        c.font = Font(bold=True)
        c.border = BORDE
        for j, y in enumerate(anios, start=2):
            cel = ws.cell(row=r, column=j, value=por_anio[y][w])
            cel.alignment = CENTRO
            cel.border = BORDE
        cel = ws.cell(row=r, column=2 + len(anios), value=sum(por_anio[y][w] for y in anios))
        cel.alignment = CENTRO
        cel.font = Font(bold=True)
        cel.border = BORDE
    r = 6
    c = ws.cell(row=r, column=1, value="Diferencia máx-mín")
    c.font = Font(italic=True)
    c.border = BORDE
    for j, y in enumerate(anios, start=2):
        cel = ws.cell(row=r, column=j, value=max(por_anio[y]) - min(por_anio[y]))
        cel.alignment = CENTRO
        cel.border = BORDE
    tot = [sum(por_anio[y][w] for y in anios) for w in range(motor.N_TRAB)]
    cel = ws.cell(row=r, column=2 + len(anios), value=max(tot) - min(tot))
    cel.alignment = CENTRO
    cel.border = BORDE
    _anchos(ws, [22] + [10] * (len(anios) + 1))


def _hoja_auditoria(wb, aud):
    ws = wb.create_sheet("Auditoría")
    _cabecera(ws, 1, ["Condición", "Estado", "Detalle"])
    for r, a in enumerate(aud, start=2):
        ws.cell(row=r, column=1, value=a["nombre"]).border = BORDE
        e = ws.cell(row=r, column=2, value="OK" if a["ok"] else "REVISAR")
        e.alignment = CENTRO
        e.border = BORDE
        e.font = Font(bold=True, color="2E7D32" if a["ok"] else "C00000")
        ws.cell(row=r, column=3, value=a["detalle"]).border = BORDE
    _anchos(ws, [70, 11, 90])


def crear_libro(res, bloques, aud, anios=None):
    """Devuelve los bytes de un .xlsx con las hojas de los años indicados (por defecto, todos)."""
    anios = list(anios or motor.ANIOS)
    wb = Workbook()
    wb.remove(wb.active)
    for y in anios:
        _hoja_anual(wb, y, res)
    _hoja_vacaciones(wb, bloques, anios)
    _hoja_festivos(wb, res, anios)
    _hoja_resumen(wb, res, anios)
    _hoja_auditoria(wb, aud)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
