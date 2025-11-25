from collections import defaultdict

def agregar_resumen(resultados_por_pdf):
    """
    Agrega los resultados diarios en resúmenes por mes y global.
    Ahora soporta múltiples tramos por día: cada tramo se suma al mes y al global.
    """
    resumen = {
        "por_mes": defaultdict(lambda: {"minutos": 0, "importe": 0.0, "dias": 0}),
        "global": {"minutos": 0, "importe": 0.0, "dias": 0}
    }

    for doc in resultados_por_pdf:
        # Para evitar contar varias veces el mismo día, llevamos un set
        dias_con_nocturnidad = set()

        for d in doc["dias"]:
            minutos = d["minutos_nocturnos"]
            importe = float(d["importe"])
            fecha = d["fecha"]

            if minutos > 0:
                try:
                    partes = fecha.split("/")
                    mes, anio = partes[1], partes[2]
                    clave = f"{mes}/{anio}"
                except Exception:
                    clave = "desconocido"

                resumen["por_mes"][clave]["minutos"] += minutos
                resumen["por_mes"][clave]["importe"] += importe

                # Contamos el día solo una vez aunque tenga varios tramos
                if fecha not in dias_con_nocturnidad:
                    resumen["por_mes"][clave]["dias"] += 1
                    resumen["global"]["dias"] += 1
                    dias_con_nocturnidad.add(fecha)

                resumen["global"]["minutos"] += minutos
                resumen["global"]["importe"] += importe

    return resumen
