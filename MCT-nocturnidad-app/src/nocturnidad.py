from datetime import datetime

def _parse_hhmm(s):
    try:
        h, m = s.split(":")
        h = int(h); m = int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return datetime.strptime(f"{h:02d}:{m:02d}", "%H:%M")
    except:
        return None
    return None

def _tarifa_por_fecha(fecha_str):
    try:
        f = datetime.strptime(fecha_str, "%d/%m/%Y")
    except:
        f = datetime.today()
    return 0.05 if f <= datetime(2025, 4, 25) else 0.062

def _minutos_nocturnos(hi_dt, hf_dt):
    minutos = 0
    tramos = [
        (datetime.strptime("22:00", "%H:%M"), datetime.strptime("23:59", "%H:%M")),
        (datetime.strptime("00:00", "%H:%M"), datetime.strptime("00:59", "%H:%M")),
        (datetime.strptime("04:00", "%H:%M"), datetime.strptime("06:00", "%H:%M")),
    ]
    for ini, fin in tramos:
        if hi_dt <= fin and hf_dt >= ini:
            o_ini = max(hi_dt, ini)
            o_fin = min(hf_dt, fin)
            if o_ini < o_fin:
                minutos += int((o_fin - o_ini).total_seconds() / 60)
    return minutos

def calcular_nocturnidad_por_dia(registros):
    resultados = []
    for r in registros:
        hi_dt = _parse_hhmm(r["hi"])
        hf_dt = _parse_hhmm(r["hf"])
        if not hi_dt or not hf_dt:
            continue

        minutos = _minutos_nocturnos(hi_dt, hf_dt)
        tarifa = _tarifa_por_fecha(r["fecha"])
        resultados.append({
            "fecha": r["fecha"],
            "hi": r["hi"],
            "hf": r["hf"],
            "minutos_nocturnos": minutos,
            "importe": f"{minutos * tarifa:.2f}",
            "principal": r.get("principal", True)
        })
    return resultados
