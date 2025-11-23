from datetime import datetime, timedelta

def parse_time(hhmm: str):
    return datetime.strptime(hhmm, "%H:%M").time()

def parse_date_ddmmyyyy(s: str):
    return datetime.strptime(s, "%d/%m/%Y").date()

def minutos_solape(a_ini, a_fin, b_ini, b_fin):
    # a_ini, a_fin, b_ini, b_fin son datetime (con fecha)
    inicio = max(a_ini, b_ini)
    fin = min(a_fin, b_fin)
    if fin <= inicio:
        return 0
    return int((fin - inicio).total_seconds() // 60)

def tarifa_por_fecha(fecha):
    # 0,05 €/min hasta 25/04/2025 incluido; 0,062 desde 26/04/2025
    if fecha <= datetime(2025, 4, 25).date():
        return 0.05
    else:
        return 0.062

def construir_dt(date_obj, time_obj):
    return datetime.combine(date_obj, time_obj)

def add_day(dt, days=1):
    return dt + timedelta(days=days)