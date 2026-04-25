import requests, json

r = requests.post(
    'http://127.0.0.1:8000/api/query',
    json={'query': 'Why did operating profit change for Castrol India Ltd in Q2 2024 compared to Q2 2021?'},
    timeout=20
)
data = r.json()
result = data['result']
change = result['change']
drivers = result['drivers']

print('=== ANALYSIS RESULT ===')
print('Operating Profit: {} -> {} ({}% {})'.format(
    change['prev_value'], change['current_value'],
    change['pct'], change['direction']
))
print()
print('=== FORMULA DRIVERS (with sub-drivers) ===')
for d in drivers:
    if d['relationship_type'] == 'formula_dependency':
        print('  {} | {} -> {} | contrib={} ({}%)'.format(
            d['display_name'], d['prev_value'], d['current_value'],
            d['contribution'], d['contribution_pct']
        ))
        for sd in d.get('sub_drivers', []):
            print('    L2: {} | contrib={} ({}%)'.format(
                sd['display_name'], sd['contribution'], sd['contribution_pct']
            ))

print()
print('=== CAUSAL CONTEXT DRIVERS ===')
for d in drivers:
    if d['relationship_type'] == 'causal_driver':
        print('  {} | {} -> {} | change_pct={}%'.format(
            d['display_name'], d['prev_value'], d['current_value'], d['change_pct']
        ))

total_contrib = sum(d['contribution'] or 0 for d in drivers if d['relationship_type'] == 'formula_dependency')
print()
print('Sum of formula contributions: {}'.format(round(total_contrib, 2)))
print('Actual DB change: {}'.format(change['absolute']))
print('Math checks out (within 1): {}'.format(abs(total_contrib - change['absolute']) < 1.0))
print()
print('Summary:')
print(result.get('summary', '')[:500])
