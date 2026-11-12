# -*- coding: utf-8 -*-
"""
motor.py
Motor de cuadrantes de guardias de 24 horas para 4 trabajadores (A, B, C, D).

Reglas implementadas
--------------------
* Periodo: del 01/01/2027 al 31/12/2030.
  El 01/01/2027 trabaja D, el 02 A, el 03 B y el 04 C.
* Cadencia fija A -> B -> C -> D: una guardia de 24 h al día, un solo trabajador.
    - Con nadie de vacaciones: 24 h de trabajo y 3 días libres.
    - Con un trabajador de vacaciones: 24 h de trabajo y 2 días libres.
  Se consigue saltando, dentro del orden fijo, al trabajador que está de vacaciones.
* Vacaciones de verano (16/06 - 15/09): un tramo de 15 días por trabajador y año.
  Vacaciones de invierno (16/09 - 15/06): un tramo de 15 días por trabajador y periodo.
  Los tramos son cíclicos: cada año (o periodo) cada trabajador pasa al tramo siguiente.
* Los días 24, 25 y 31 de diciembre, 1 de enero, Jueves Santo y Viernes Santo deben
  rotar: cada uno de esos días lo trabaja un trabajador distinto en cada uno de los 4 años.
"""
from __future__ import annotations

import datetime as dt
import random
import time
from dataclasses import dataclass

# --------------------------------------------------------------------------- constantes
TRABAJADORES = ["A", "B", "C", "D"]
N_TRAB = len(TRABAJADORES)
FECHA_INICIO = dt.date(2027, 1, 1)
FECHA_FIN = dt.date(2030, 12, 31)
ANIOS = list(range(FECHA_INICIO.year, FECHA_FIN.year + 1))
ANIO_INICIO = FECHA_INICIO.year
N_DIAS = (FECHA_FIN - FECHA_INICIO).days + 1
PRIMER_TRABAJADOR = 3                 # el 01/01/2027 trabaja D
INICIO_ESPERADO = [3, 0, 1, 2]        # D, A, B, C (1 a 4 de enero de 2027)
DIAS_VAC = 15

# Posibles inicios (mes, día) de los tramos de 15 días
OPCIONES_VERANO = [(6, 16), (7, 1), (7, 16), (8, 1), (8, 16), (9, 1)]
OPCIONES_INVIERNO = [(9, 16), (10, 1), (10, 16), (11, 1), (11, 16), (12, 1), (12, 16),
                     (1, 1), (1, 16), (2, 1), (2, 16), (3, 1), (3, 16), (4, 1), (4, 16),
                     (5, 1), (5, 16), (6, 1)]

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]
DIAS_SEMANA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

NOMBRES_FESTIVOS = ["24 de diciembre", "25 de diciembre", "31 de diciembre",
                    "1 de enero", "Jueves Santo", "Viernes Santo"]


# --------------------------------------------------------------------------- utilidades
def clave_invierno(tramo):
    """Orden cronológico dentro del periodo de invierno (de septiembre a junio)."""
    return ((tramo[0] - 9) % 12) * 100 + tramo[1]


def etiqueta_tramo(mes, dia):
    ini = dt.date(2027, mes, dia)
    fin = ini + dt.timedelta(days=DIAS_VAC - 1)
    return f"{ini.day} {MESES[ini.month - 1]} → {fin.day} {MESES[fin.month - 1]}"


def pascua(anio):
    """Domingo de Pascua (calendario gregoriano, algoritmo de Meeus/Jones/Butcher)."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(anio, mes, dia)


def festivos(anio):
    """Los seis días que deben rotar entre los trabajadores."""
    p = pascua(anio)
    return {
        "24 de diciembre": dt.date(anio, 12, 24),
        "25 de diciembre": dt.date(anio, 12, 25),
        "31 de diciembre": dt.date(anio, 12, 31),
        "1 de enero": dt.date(anio, 1, 1),
        "Jueves Santo": p - dt.timedelta(days=3),
        "Viernes Santo": p - dt.timedelta(days=2),
    }


def _idx(fecha):
    return (fecha - FECHA_INICIO).days


_FEST_IDX = {n: [_idx(festivos(y)[n]) for y in ANIOS] for n in NOMBRES_FESTIVOS}
_FEST_SET = {k for v in _FEST_IDX.values() for k in v}
_ANIO_IDX = [(FECHA_INICIO + dt.timedelta(days=i)).year - ANIO_INICIO for i in range(N_DIAS)]


# --------------------------------------------------------------------------- configuración
@dataclass
class Config:
    """
    tramos_verano / tramos_invierno : 4 inicios (mes, día), ordenados cronológicamente.
    asig_verano[w]   : índice del tramo de verano del trabajador w en 2027; cada año pasa al siguiente.
    asig_invierno[w] : índice del tramo de invierno del trabajador w en el periodo 16/09/2026-15/06/2027;
                       cada periodo pasa al siguiente.
    """
    tramos_verano: list
    tramos_invierno: list
    asig_verano: list
    asig_invierno: list

    def a_dict(self):
        return {
            "tramos_verano": [list(t) for t in self.tramos_verano],
            "tramos_invierno": [list(t) for t in self.tramos_invierno],
            "asig_verano": list(self.asig_verano),
            "asig_invierno": list(self.asig_invierno),
        }

    @staticmethod
    def de_dict(d):
        return Config(
            [tuple(t) for t in d["tramos_verano"]],
            [tuple(t) for t in d["tramos_invierno"]],
            list(d["asig_verano"]),
            list(d["asig_invierno"]),
        )


# Combinación recomendada: cumple todas las condiciones y reparte las guardias casi a la par.
CONFIG_RECOMENDADA = Config(
    tramos_verano=[(7, 1), (7, 16), (8, 1), (8, 16)],
    tramos_invierno=[(2, 1), (3, 1), (5, 16), (6, 1)],
    asig_verano=[1, 0, 3, 2],       # 2027: A 16/07, B 01/07, C 16/08, D 01/08
    asig_invierno=[2, 3, 0, 1],     # 2026-27: A 16/05, B 01/06, C 01/02, D 01/03
)


def validar_config(cfg):
    """Devuelve una lista de mensajes de error (vacía si la configuración es coherente)."""
    err = []
    for nombre, tr in (("verano", cfg.tramos_verano), ("invierno", cfg.tramos_invierno)):
        if len(tr) != 4 or len({tuple(t) for t in tr}) != 4:
            err.append(f"Hacen falta 4 tramos distintos de {nombre}.")
    for nombre, a in (("verano", cfg.asig_verano), ("invierno", cfg.asig_invierno)):
        if sorted(a) != [0, 1, 2, 3]:
            err.append(f"Cada trabajador debe tener un tramo de {nombre} distinto en el reparto inicial.")
    if err:
        return err
    for m, d in cfg.tramos_verano:
        ini = dt.date(2027, m, d)
        fin = ini + dt.timedelta(days=DIAS_VAC - 1)
        if ini < dt.date(2027, 6, 16) or fin > dt.date(2027, 9, 15):
            err.append(f"El tramo de verano que empieza el {d:02d}/{m:02d} se sale del 16/06 - 15/09.")
    for m, d in cfg.tramos_invierno:
        ini = dt.date(2026 if m >= 9 else 2027, m, d)
        fin = ini + dt.timedelta(days=DIAS_VAC - 1)
        if ini < dt.date(2026, 9, 16) or fin > dt.date(2027, 6, 15):
            err.append(f"El tramo de invierno que empieza el {d:02d}/{m:02d} se sale del 16/09 - 15/06.")
    return err


# --------------------------------------------------------------------------- generación
def bloques_vacaciones(cfg):
    """Lista de bloques de vacaciones que afectan al periodo 2027-2030."""
    bloques = []
    for y in ANIOS:
        for w in range(N_TRAB):
            m, d = cfg.tramos_verano[(cfg.asig_verano[w] + y - ANIO_INICIO) % 4]
            ini = dt.date(y, m, d)
            bloques.append({"trabajador": w, "tipo": "Verano", "periodo": str(y), "inicio": ini,
                            "fin": ini + dt.timedelta(days=DIAS_VAC - 1)})
    for p in range(len(ANIOS) + 1):
        for w in range(N_TRAB):
            m, d = cfg.tramos_invierno[(cfg.asig_invierno[w] + p) % 4]
            anio = ANIO_INICIO - 1 + p if m >= 9 else ANIO_INICIO + p
            ini = dt.date(anio, m, d)
            bloques.append({"trabajador": w, "tipo": "Invierno",
                            "periodo": f"{ANIO_INICIO - 1 + p}-{ANIO_INICIO + p}", "inicio": ini,
                            "fin": ini + dt.timedelta(days=DIAS_VAC - 1)})
    return [b for b in bloques if b["fin"] >= FECHA_INICIO and b["inicio"] <= FECHA_FIN]


def generar(cfg):
    """Devuelve (res, bloques, vac). res[i] = trabajador de guardia el día i (0=A ... 3=D)."""
    bloques = bloques_vacaciones(cfg)
    vac = [[] for _ in range(N_DIAS)]
    for b in bloques:
        d = b["inicio"]
        while d <= b["fin"]:
            i = _idx(d)
            if 0 <= i < N_DIAS:
                vac[i].append(b["trabajador"])
            d += dt.timedelta(days=1)
    res = [PRIMER_TRABAJADOR]
    for i in range(1, N_DIAS):
        prev = res[-1]
        elegido = None
        for k in range(1, N_TRAB + 1):
            c = (prev + k) % N_TRAB
            if c not in vac[i]:
                elegido = c
                break
        res.append(elegido if elegido is not None else (prev + 1) % N_TRAB)
    return res, bloques, vac


# --------------------------------------------------------------------------- estadísticas
def guardias_por_anio(res):
    """{año: [guardias de A, B, C, D]}"""
    out = {y: [0] * N_TRAB for y in ANIOS}
    for i, w in enumerate(res):
        out[ANIO_INICIO + _ANIO_IDX[i]][w] += 1
    return out


def guardias_por_mes(res, anio):
    """{letra: [guardias en cada mes]} para un año."""
    out = {L: [0] * 12 for L in TRABAJADORES}
    d = dt.date(anio, 1, 1)
    while d.year == anio:
        i = _idx(d)
        if 0 <= i < N_DIAS:
            out[TRABAJADORES[res[i]]][d.month - 1] += 1
        d += dt.timedelta(days=1)
    return out


def matriz_anual(res, anio):
    """Cuadrícula 31 días x 12 meses: letra del trabajador ('' si el día no existe) y marca de festivo."""
    letras = [[""] * 12 for _ in range(31)]
    fest = [[False] * 12 for _ in range(31)]
    fset = set(festivos(anio).values())
    d = dt.date(anio, 1, 1)
    while d.year == anio:
        i = _idx(d)
        if 0 <= i < N_DIAS:
            letras[d.day - 1][d.month - 1] = TRABAJADORES[res[i]]
            fest[d.day - 1][d.month - 1] = d in fset
        d += dt.timedelta(days=1)
    return letras, fest


# --------------------------------------------------------------------------- auditoría
def _f(i):
    return (FECHA_INICIO + dt.timedelta(days=i)).strftime("%d/%m/%Y")


def auditar(bloques, res, vac):
    """Comprueba todas las condiciones. Devuelve una lista de {'nombre', 'ok', 'detalle'}."""
    checks = []

    def add(nombre, ok, detalle):
        checks.append({"nombre": nombre, "ok": bool(ok), "detalle": detalle})

    ini = res[:4]
    add("Arranque: 1 de enero de 2027 = D, A, B, C", ini == INICIO_ESPERADO,
        "Días 1 a 4 de enero: " + ", ".join(TRABAJADORES[i] for i in ini))
    add("Periodo cubierto", True, f"{FECHA_INICIO:%d/%m/%Y} a {FECHA_FIN:%d/%m/%Y} ({N_DIAS} días)")

    solapes = [i for i in range(N_DIAS) if len(vac[i]) > 1]
    add("Nunca hay dos trabajadores de vacaciones a la vez", not solapes,
        "Sin solapes." if not solapes else f"{len(solapes)} días con solape, el primero el {_f(solapes[0])}.")

    incoh = [i for i in range(N_DIAS) if res[i] in vac[i]]
    add("Nadie trabaja estando de vacaciones", not incoh,
        "Correcto." if not incoh else f"Hay guardias en días de vacaciones, la primera el {_f(incoh[0])}.")

    faltan = []
    for y in ANIOS:
        for w in range(N_TRAB):
            n = sum(1 for b in bloques if b["tipo"] == "Verano" and b["trabajador"] == w
                    and b["inicio"].year == y)
            if n != 1:
                faltan.append(f"{TRABAJADORES[w]} {y}")
    add("Cada trabajador tiene 15 días de vacaciones de verano cada año", not faltan,
        "4 trabajadores x 4 años." if not faltan else "Falta o sobra en: " + ", ".join(faltan))

    viol = [i for i in range(1, N_DIAS) if not vac[i] and res[i] != (res[i - 1] + 1) % N_TRAB]
    add("Cadencia inmodificable A → B → C → D cuando nadie está de vacaciones", not viol,
        "El orden nunca se altera fuera de vacaciones." if not viol
        else f"{len(viol)} saltos de orden, el primero el {_f(viol[0])}.")

    ult = [None] * N_TRAB
    n3 = n4 = 0
    anom = []
    for i, w in enumerate(res):
        if ult[w] is not None:
            g = i - ult[w]
            if g == 3:
                n3 += 1
            elif g == 4:
                n4 += 1
            elif not any(w in vac[k] for k in range(ult[w] + 1, i)):
                anom.append(f"{TRABAJADORES[w]}: {_f(ult[w])} y {_f(i)} ({g - 1} libres)")
        ult[w] = i
    add("Entre guardias siempre hay 2 o 3 días libres (salvo en sus vacaciones)", not anom,
        f"{n4} descansos de 3 días libres y {n3} de 2 días libres." if not anom
        else f"{len(anom)} casos anómalos, p. ej. " + "; ".join(anom[:3]))

    en_fest = []
    for y in ANIOS:
        for nombre, f in festivos(y).items():
            i = _idx(f)
            if 0 <= i < N_DIAS and vac[i]:
                en_fest.append(f"{nombre} {y}")
    add("Ninguna vacación cae en los 6 días señalados", not en_fest,
        "Correcto." if not en_fest else "Vacaciones en: " + ", ".join(en_fest))

    mal = []
    for nombre in NOMBRES_FESTIVOS:
        ws = [res[k] for k in _FEST_IDX[nombre]]
        if len(set(ws)) != 4:
            mal.append(f"{nombre} ({'-'.join(TRABAJADORES[w] for w in ws)})")
    add("Rotación de festivos: cada día señalado lo trabaja uno distinto cada año", not mal,
        "24, 25 y 31 dic, 1 ene, Jueves y Viernes Santo rotan entre los 4." if not mal
        else "Se repite en: " + ", ".join(mal))

    por_anio = guardias_por_anio(res)
    difs = {y: max(c) - min(c) for y, c in por_anio.items()}
    add("Reparto de guardias por año (diferencia máxima de 2)", max(difs.values()) <= 2,
        ", ".join(f"{y}: {d}" for y, d in difs.items()))
    tot = [sum(por_anio[y][w] for y in ANIOS) for w in range(N_TRAB)]
    add("Reparto total de guardias en los 4 años (diferencia máxima de 2)", max(tot) - min(tot) <= 2,
        ", ".join(f"{TRABAJADORES[w]}: {tot[w]}" for w in range(N_TRAB)))
    return checks


# --------------------------------------------------------------------------- buscador (rápido)
def _marcar(mask, w, ini):
    k0 = (ini - FECHA_INICIO).days
    for k in range(k0, k0 + DIAS_VAC):
        if 0 <= k < N_DIAS:
            if mask[k]:
                return False
            mask[k] = w + 1
    return True


def _mascara(tv, tw, av, aw):
    mask = [0] * N_DIAS
    for y in ANIOS:
        for w in range(N_TRAB):
            m, d = tv[(av[w] + y - ANIO_INICIO) % 4]
            if not _marcar(mask, w, dt.date(y, m, d)):
                return None
    for p in range(len(ANIOS) + 1):
        for w in range(N_TRAB):
            m, d = tw[(aw[w] + p) % 4]
            anio = ANIO_INICIO - 1 + p if m >= 9 else ANIO_INICIO + p
            if not _marcar(mask, w, dt.date(anio, m, d)):
                return None
    return mask


def _simular(mask):
    res = [0] * N_DIAS
    res[0] = prev = PRIMER_TRABAJADOR
    for i in range(1, N_DIAS):
        c = (prev + 1) & 3
        if c == mask[i] - 1:
            c = (c + 1) & 3
        res[i] = prev = c
    return res


def _rotan(res):
    return all(len({res[k] for k in ks}) == 4 for ks in _FEST_IDX.values())


def _huecos_ok(res, mask):
    ult = [None] * N_TRAB
    for i in range(N_DIAS):
        w = res[i]
        if ult[w] is not None:
            g = i - ult[w]
            if g != 3 and g != 4:
                if not any(mask[k] == w + 1 for k in range(ult[w] + 1, i)):
                    return False
        ult[w] = i
    return True


def _dispersion(res):
    cont = [[0] * N_TRAB for _ in ANIOS]
    for i in range(N_DIAS):
        cont[_ANIO_IDX[i]][res[i]] += 1
    max_anual = max(max(c) - min(c) for c in cont)
    tot = [sum(cont[a][w] for a in range(len(ANIOS))) for w in range(N_TRAB)]
    return max_anual, max(tot) - min(tot)


def buscar(fijar_verano=True, segundos=30, semilla=None, progreso=None):
    """
    Busca una combinación (tramos + reparto inicial) que cumpla TODAS las condiciones y
    reparta las guardias lo más igualado posible.
    fijar_verano=True mantiene los tramos 1-15 y 16-30 de julio y agosto.
    progreso(segundos, probadas, validas, mejor) se llama unas 4 veces por segundo.
    """
    rnd = random.Random(semilla)
    t0 = time.time()
    ultimo = 0.0
    probadas = validas = 0
    mejor = None
    while True:
        ahora = time.time()
        if ahora - t0 >= segundos:
            break
        if progreso and ahora - ultimo > 0.25:
            progreso(ahora - t0, probadas, validas, mejor[0] if mejor else None)
            ultimo = ahora
        probadas += 1
        tv = [(7, 1), (7, 16), (8, 1), (8, 16)] if fijar_verano else sorted(rnd.sample(OPCIONES_VERANO, 4))
        tw = sorted(rnd.sample(OPCIONES_INVIERNO, 4), key=clave_invierno)
        av = rnd.sample(range(N_TRAB), N_TRAB)
        aw = rnd.sample(range(N_TRAB), N_TRAB)
        mask = _mascara(tv, tw, av, aw)
        if mask is None or mask[0] == PRIMER_TRABAJADOR + 1:
            continue
        if any(mask[k] for k in _FEST_SET):
            continue
        res = _simular(mask)
        if res[:4] != INICIO_ESPERADO or not _rotan(res) or not _huecos_ok(res, mask):
            continue
        validas += 1
        clave = _dispersion(res)
        if mejor is None or clave < mejor[0]:
            mejor = (clave, Config(tv, tw, av, aw))
            if clave <= (1, 1):
                break
    if mejor is None:
        return None
    return {"config": mejor[1], "probadas": probadas, "validas": validas,
            "segundos": time.time() - t0, "disp_anual": mejor[0][0], "disp_total": mejor[0][1]}


# --------------------------------------------------------------------------- prueba rápida
if __name__ == "__main__":
    cfg = CONFIG_RECOMENDADA
    res, bloques, vac = generar(cfg)
    print("Errores de configuración:", validar_config(cfg) or "ninguno")
    for c in auditar(bloques, res, vac):
        print("OK " if c["ok"] else "MAL", c["nombre"], "-", c["detalle"])
