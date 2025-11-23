from datetime import time
from .utils import construir_dt, minutos_solape, tarifa_por_fecha

FRANJAS = [
    # Franja nocturna 1: 22:00–00:59 (cruza medianoche)
    ('22:00', '00:59'),
    # Franja nocturna 2: 04:00–06:00 (mismo día)
    ('04:00', '06:00'),
]

def _time_from_str(s):
    hh, mm = s.split(':')
    return time(int(hh), int(mm))

def _split_pair(pair_str):
    # "HH:MM HH:MM" -> (time1, time2)
    a, b = pair_str.strip().split()
    return _time_from_str(a), _time_from_str(b)

def _franjas_dt(fecha):
    # Construye las franjas con fecha concreta y con cruce de día cuando aplique
    f1_ini = time(22, 0); f1_fin = time(0, 59)
    f2_ini = time(4, 0);  f2_fin = time(6, 0)
    # f1 cruza medianoche: inicio en fecha, fin en fecha+1
    return [
        (construir_dt(fecha, f1_ini), construir_dt(fecha, f1_fin).replace(day=fecha.day) if f1_fin > f1_ini else construir_dt(fecha, f1_fin).replace(day=fecha.day+1)),
        (construir_dt(fecha, f2_ini), construir_dt(fecha, f2_fin))
    ]

def calcular_nocturnidad_por_dia(registros):
    resultados = []
    for r in registros:
        fecha = r['fecha']
        tarifa = tarifa_por_fecha(fecha)
        minutos = 0

        tramos = []
        if r.get('hi'):
            a, b = _split_pair(r['hi'])
            tramos.append((a, b))
        if r.get('hf'):
            a, b = _split_pair(r['hf'])
            tramos.append((a, b))

        franjas_dt = _franjas_dt(fecha)

        for (t_ini, t_fin) in tramos:
            # tramo puede cruzar medianoche si t_fin < t_ini => pasa al día siguiente
            tramo_ini_dt = construir_dt(fecha, t_ini)
            tramo_fin_dt = construir_dt(fecha, t_fin)
            if t_fin < t_ini:
                # cruzó medianoche
                tramo_fin_dt = tramo_fin_dt.replace(day=fecha.day+1)

            for (f_ini, f_fin) in franjas_dt:
                minutos += minutos_solape(tramo_ini_dt, tramo_fin_dt, f_ini, f_fin)

        importe = round(minutos * tarifa, 2)
        resultados.append({
            'fecha': fecha.strftime("%d/%m/%Y"),
            'minutos_nocturnos': minutos,
            'importe': f"{importe:.2f}"
        })
    return resultados