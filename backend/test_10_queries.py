import sys, os
os.environ.setdefault('DATABASE_URL', open('.env').read().split('DATABASE_URL=')[1].split()[0])
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.data.financial_accessor import FinancialDataAccessor

db = SessionLocal()
acc = FinancialDataAccessor(db)

tests = [
    # Clean quarter-over-quarter and year-over-year tests
    ('ASK Automotive Ltd',                   'Q4 2025', 'Q2 2025', 'operating_profit'),
    ('ASK Automotive Ltd',                   'Q4 2025', 'Q2 2025', 'revenue_from_operations'),
    ('ASK Automotive Ltd',                   'Q4 2025', 'Q2 2025', 'pnl_for_period'),
    ('ASK Automotive Ltd',                   'Q4 2025', 'Q2 2025', 'cost_of_material'),
    ('Castrol India Ltd',                    'Q2 2025', 'Q2 2024', 'operating_profit'),
    ('Castrol India Ltd',                    'Q2 2025', 'Q2 2024', 'revenue_from_operations'),
    ('Castrol India Ltd',                    'Q2 2024', 'Q2 2023', 'operating_profit'),
    ('Amara Raja Energy & Mobility Ltd',     'Q2 2025', 'Q2 2024', 'operating_profit'),
    ('Alicon Castalloy Ltd',                 'Q2 2025', 'Q2 2024', 'revenue_from_operations'),
    ('Akar Auto Industries Ltd',             'Q2 2025', 'Q2 2024', 'pnl_for_period'),
]

for i, (company, period, compare, metric) in enumerate(tests, 1):
    curr = acc.get_metric_value(metric, company, period)
    prev = acc.get_metric_value(metric, company, compare)
    if curr is not None and prev is not None and prev != 0:
        pct = (curr - prev) / abs(prev) * 100
        pct_str = "{:+.1f}%".format(pct)
    else:
        pct_str = 'N/A'
    curr_str = "{:.2f}".format(curr) if curr is not None else 'None'
    prev_str = "{:.2f}".format(prev) if prev is not None else 'None'
    print("Q{}: {} | {} | {} vs {} | curr={} prev={} {}".format(
        i, company, metric, period, compare, curr_str, prev_str, pct_str))

db.close()
