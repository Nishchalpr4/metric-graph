import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
db_url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(db_url)
cur = conn.cursor()

print('=== VERIFYING OPERATING PROFIT NUMBERS ===\n')

# Get Castrol India Ltd
cur.execute('''
SELECT company_id, official_legal_name
FROM mappings_canonical_companies
WHERE official_legal_name ILIKE '%Castrol%'
''')
castrol_id, castrol_name = cur.fetchone()
print(f'Company: {castrol_name} (ID: {castrol_id})\n')

# Get all filings for Q2 2024 and Q2 2021
cur.execute('''
SELECT filing_id, reporting_end_date 
FROM financials_filing
WHERE company_id = %s
  AND EXTRACT(QUARTER FROM reporting_end_date) = 2
  AND EXTRACT(YEAR FROM reporting_end_date) IN (2024, 2021)
ORDER BY reporting_end_date DESC
''', (castrol_id,))

filings = cur.fetchall()
print(f'Found {len(filings)} filings for Q2 2024 and Q2 2021\n')

results = {}
for filing_id, report_date in filings:
    year = report_date.year
    
    # Get base metrics from this filing
    cur.execute('''
    SELECT operating_profit, revenue_from_operations,
           cost_of_material, employee_benefit_expense, depreciation, 
           other_expenses, profit_before_tax, pnl_for_period
    FROM financials_pnl
    WHERE filing_id = %s
    ''', (filing_id,))
    
    row = cur.fetchone()
    if row:
        op_profit, revenue, com, emp_benefit, depr, other_exp, pbt, net_profit = row
        
        if year not in results:
            results[year] = {
                'filing_id': filing_id,
                'date': report_date,
                'operating_profit': op_profit,
                'revenue': revenue,
                'cost_of_material': com,
                'employee_benefit': emp_benefit,
                'depreciation': depr,
                'other_expenses': other_exp,
                'profit_before_tax': pbt,
                'net_profit': net_profit
            }

# Display results
print('Q2 2024 Metrics:')
if 2024 in results:
    r = results[2024]
    print(f'  Date: {r["date"]}')
    print(f'  Operating Profit: {r["operating_profit"]}')
    print(f'  Profit Before Tax: {r["profit_before_tax"]}')
    print(f'  Net Profit (PNL for Period): {r["net_profit"]}')
    print(f'  Revenue From Operations: {r["revenue"]}')
    print(f'  Cost of Material: {r["cost_of_material"]}')
    print(f'  Employee Benefit: {r["employee_benefit"]}')
    print(f'  Depreciation: {r["depreciation"]}')
    print(f'  Other Expenses: {r["other_expenses"]}')
else:
    print('  NO DATA FOUND')

print('\nQ2 2021 Metrics:')
if 2021 in results:
    r = results[2021]
    print(f'  Date: {r["date"]}')
    print(f'  Operating Profit: {r["operating_profit"]}')
    print(f'  Profit Before Tax: {r["profit_before_tax"]}')
    print(f'  Net Profit (PNL for Period): {r["net_profit"]}')
    print(f'  Revenue From Operations: {r["revenue"]}')
    print(f'  Cost of Material: {r["cost_of_material"]}')
    print(f'  Employee Benefit: {r["employee_benefit"]}')
    print(f'  Depreciation: {r["depreciation"]}')
    print(f'  Other Expenses: {r["other_expenses"]}')
else:
    print('  NO DATA FOUND')

# Calculate differences
print('\n=== CALCULATIONS ===\n')

if 2024 in results and 2021 in results:
    r24 = results[2024]
    r21 = results[2021]
    
    op_diff = r24['operating_profit'] - r21['operating_profit']
    op_pct = (op_diff / r21['operating_profit'] * 100) if r21['operating_profit'] else 0
    
    print(f'Operating Profit Q2 2024: {r24["operating_profit"]}')
    print(f'Operating Profit Q2 2021: {r21["operating_profit"]}')
    print(f'Difference: +{op_diff} ({op_pct:.1f}%)')
    
    print(f'\nRevenue Q2 2024: {r24["revenue"]}')
    print(f'Revenue Q2 2021: {r21["revenue"]}')
    rev_diff = r24['revenue'] - r21['revenue']
    rev_pct = (rev_diff / r21['revenue'] * 100) if r21['revenue'] else 0
    print(f'Difference: +{rev_diff} ({rev_pct:.1f}%)')
    
    print(f'\n=== VERIFICATION ===\n')
    print(f'Expected from UI: OP = 322.44, Change = +124.94 (+63.3%)')
    print(f'Actual from DB:   OP = {r24["operating_profit"]}, Change = +{op_diff} ({op_pct:.1f}%)')
    
    # Check if they match
    match_op = abs(float(r24['operating_profit']) - 322.44) < 0.01 if r24['operating_profit'] else False
    match_diff = abs(float(op_diff) - 124.94) < 0.01 if op_diff else False
    match_pct = abs(float(op_pct) - 63.3) < 0.1
    
    print(f'\n✓ Operating Profit CORRECT: {r24["operating_profit"]}' if match_op else f'\n✗ Operating Profit mismatch')
    print(f'✓ Difference CORRECT: +{op_diff} ({float(op_pct):.1f}%)' if match_diff else f'✗ Difference mismatch')
    print(f'✓ Percentage CORRECT' if match_pct else f'✗ Percentage mismatch')

cur.close()
conn.close()
