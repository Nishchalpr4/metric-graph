import urllib.request, json

try:
    r = urllib.request.urlopen('http://127.0.0.1:8002/api/companies-with-data', timeout=30)
    d = json.load(r)
    total = d["total"]
    names = [c["name"] for c in d["companies"][:5]]
    print(f'companies-with-data: {total} companies')
    print('First 5:', names)
    print()

    if d['companies']:
        cid = d['companies'][0]['id']
        cname = d['companies'][0]['name']
        r2 = urllib.request.urlopen(f'http://127.0.0.1:8002/api/available-data?company_id={cid}', timeout=30)
        d2 = json.load(r2)
        periods = d2["periods"]
        metric_names = [m["display_name"] for m in d2["metrics"]]
        print(f'available-data for {cname}:')
        print(f'  Periods: {periods}')
        print(f'  Metrics ({len(metric_names)}): {metric_names}')
except Exception as e:
    print('ERROR:', e)
