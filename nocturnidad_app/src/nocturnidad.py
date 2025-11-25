from datetime import datetime, timedelta

def _parse_hhmm(s):
    """
    Convierte una cadena HH:MM en datetime.
    Devuelve None si el formato no es válido.
    """
    try:
        return datetime.strptime(s, "%H:%M")
    except Exception:
        return None

def calcular_nocturnidad_por_dia(registros):
    """
    Calcula minutos de nocturnidad para una lista de tramos de un día.
    Cada tramo es un dict con 'hi' y 'hf' (HH:MM).
    """
    minutos_total = 0
    tramos_validos = []

    for r in registros:
        hi_dt = _parse_hhmm(r["hi"])
        hf_dt = _parse_hhmm(r["hf"])
        if not hi_dt or not hf_dt:
            continue

        # Evitar intervalos negativos o vacíos
        if hi_dt >= hf_dt:
            continue

        # Franja nocturna: 22:00 del mismo día → 06:00 del día siguiente
        noct_ini = hi_dt.replace(hour=22, minute=0)
        noct_fin = hi_dt.replace(hour=6, minute=0) + timedelta(days=1)

        # Calcular solapamiento
        inicio = max(hi_dt, noct_ini)
        fin = min(hf_dt, noct_fin)

        if inicio < fin:
            minutos = int((fin - inicio).total_seconds() / 60)
            minutos_total += minutos
            tramos_validos.append({**r, "minutos": minutos})

    return minutos_total, tramos_validos

def calcular_nocturnidad_global(lista_registros):
    """
    Calcula nocturnidad para todos los registros de un mes.
    Devuelve total minutos, importe y detalle por día.
    """
    resumen = {}
    total_minutos = 0
    total_dias = 0

    for r in lista_registros:
        fecha = r["fecha"]
        if fecha not in resumen:
            resumen[fecha] = []
        resumen[fecha].append(r)

    detalle = []
    for fecha, regs in resumen.items():
        minutos, tramos = calcular_nocturnidad_por_dia(regs)
        if minutos > 0:
            total_minutos += minutos
            total_dias += 1
            for t in tramos:
                detalle.append({
                    "fecha": fecha,
                    "hi": t["hi"],
                    "hf": t["hf"],
                    "minutos": t["minutos"],
                    "importe": round(t["minutos"] * 0.05, 2)  # tarifa base
                })

    total_importe = round(total_minutos * 0.05, 2)
    return {
        "detalle": detalle,
        "total_minutos": total_minutos,
        "total_importe": total_importe,
        "total_dias": total_dias
    }
