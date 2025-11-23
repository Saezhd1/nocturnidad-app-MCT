from collections import defaultdict

def agregar_por_mes_y_global(resultados_por_pdf):
    # resultados_por_pdf: [{filename, dias: [ {fecha, minutos_nocturnos, importe}, ... ]}, ...]
    por_mes = defaultdict(lambda: {'minutos': 0, 'importe': 0.0, 'dias': 0})
    total = {'minutos': 0, 'importe': 0.0, 'dias': 0}

    for doc in resultados_por_pdf:
        for d in doc['dias']:
            dd, mm, yyyy = d['fecha'].split('/')
            key = f"{mm}/{yyyy}"
            por_mes[key]['minutos'] += d['minutos_nocturnos']
            por_mes[key]['importe'] += float(d['importe'])
            por_mes[key]['dias'] += 1

            total['minutos'] += d['minutos_nocturnos']
            total['importe'] += float(d['importe'])
            total['dias'] += 1

    # formateo
    por_mes_fmt = {k: {'minutos': v['minutos'], 'importe': round(v['importe'], 2), 'dias': v['dias']} for k, v in por_mes.items()}
    total['importe'] = round(total['importe'], 2)
    return {'por_mes': por_mes_fmt, 'global': total}