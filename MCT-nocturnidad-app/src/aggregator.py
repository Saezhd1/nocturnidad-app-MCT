from collections import defaultdict

def agregar_resumen(resultados_por_pdf):
    resumen = {
        "por_mes": defaultdict(lambda: {"minutos": 0, "importe": 0.0, "dias": 0}),
        "global": {"minutos": 0, "importe": 0.0, "dias": 0}
    }

    for doc in resultados_por_pdf:
        dias_con_nocturnidad = set()
        for d in doc["dias"]:
            minutos = d["minutos_nocturnos"]
            importe = float(d["importe"])
            fecha = d["fecha"]

            if minutos > 0:
                partes = fecha.split("/")
                mes, anio = partes[1], partes[2]
                clave = f"{mes}/{anio}"

                resumen["por_mes"][clave]["minutos"] += minutos
                resumen["por_mes"][clave]["importe"] += importe

                if fecha not in dias_con_nocturnidad:
                    resumen["por_mes"][clave]["dias"] += 1
                    resumen["global"]["dias"] += 1
                    dias_con_nocturnidad.add(fecha)

                resumen["global"]["minutos"] += minutos
                resumen["global"]["importe"] += importe

    return resumen
