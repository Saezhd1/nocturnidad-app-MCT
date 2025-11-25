from datetime import datetime

def calcular_nocturnidad_por_dia(registros):
    """
    Calcula minutos nocturnos e importe por día según HI/HF.
    """
    resultados = []
    for r in registros:
        try:
            hi = datetime.strptime(r["hi"], "%H:%M")
            hf = datetime.strptime(r["hf"], "%H:%M")
        except Exception:
            continue

        minutos_nocturnos = 0

        # Tramos nocturnos: 22:00–00:59 y 04:00–06:00
        tramos = [
            (datetime.strptime("22:00", "%H:%M"), datetime.strptime("23:59", "%H:%M")),
            (datetime.strptime("00:00", "%H:%M"), datetime.strptime("00:59", "%H:%M")),
            (datetime.strptime("04:00", "%H:%M"), datetime.strptime("06:00", "%H:%M")),
        ]

        for inicio, fin in tramos:
            if hi <= fin and hf >= inicio:
                overlap_start = max(hi, inicio)
                overlap_end = min(hf, fin)
                if overlap_start < overlap_end:
                    minutos_nocturnos += int((overlap_end - overlap_start).total_seconds() / 60)

        # Tarifa: 0.05 €/min hasta 25/04/2025, luego 0.062 €/min
        fecha = r["fecha"]
        try:
            fecha_dt = datetime.strptime(fecha, "%d/%m/%Y")
        except Exception:
            fecha_dt = datetime.today()

        if fecha_dt <= datetime(2025, 4, 25):
            tarifa = 0.05
        else:
            tarifa = 0.062

        importe = minutos_nocturnos * tarifa

        resultados.append({
            "fecha": fecha,
            "hi": r["hi"],
            "hf": r["hf"],
            "minutos_nocturnos": minutos_nocturnos,
            "importe": f"{importe:.2f}"
        })

    return resultados
