from datetime import datetime

def calcular_nocturnidad_por_dia(registros):
    resultados = []
    for r in registros:
        fecha = r["fecha"]
        hi = r["hi"]
        hf = r["hf"]

        try:
            hi_dt = datetime.strptime(hi, "%H:%M")
            hf_dt = datetime.strptime(hf, "%H:%M")
        except Exception:
            continue

        minutos_nocturnos = 0
        tramos = [
            (datetime.strptime("22:00", "%H:%M"), datetime.strptime("23:59", "%H:%M")),
            (datetime.strptime("00:00", "%H:%M"), datetime.strptime("00:59", "%H:%M")),
            (datetime.strptime("04:00", "%H:%M"), datetime.strptime("06:00", "%H:%M")),
        ]

        for inicio, fin in tramos:
            if hi_dt <= fin and hf_dt >= inicio:
                overlap_start = max(hi_dt, inicio)
                overlap_end = min(hf_dt, fin)
                if overlap_start < overlap_end:
                    minutos_nocturnos += int((overlap_end - overlap_start).total_seconds() / 60)

        try:
            fecha_dt = datetime.strptime(fecha, "%d/%m/%Y")
        except Exception:
            fecha_dt = datetime.today()

        tarifa = 0.05 if fecha_dt <= datetime(2025, 4, 25) else 0.062
        importe = minutos_nocturnos * tarifa

        resultados.append({
            "fecha": fecha,
            "hi": hi,
            "hf": hf,
            "minutos_nocturnos": minutos_nocturnos,
            "importe": f"{importe:.2f}"
        })

    return resultados
