from datetime import datetime

def calcular_nocturnidad_por_dia(registros):
    resultados = []
    for r in registros:
        try:
            hi_dt = datetime.strptime(r["hi"], "%H:%M")
            hf_dt = datetime.strptime(r["hf"], "%H:%M")
        except Exception:
            continue

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

        try:
            fecha_dt = datetime.strptime(r["fecha"], "%d/%m/%Y")
        except Exception:
            fecha_dt = datetime.today()
        tarifa = 0.05 if fecha_dt <= datetime(2025, 4, 25) else 0.062

        resultados.append({
            "fecha": r["fecha"],
            "hi": r["hi"],
            "hf": r["hf"],
            "minutos_nocturnos": minutos,
            "importe": f"{minutos * tarifa:.2f}",
        })
    return resultados
