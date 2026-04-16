#!/usr/bin/env python
"""
Populate Neon database with time_series_data using raw psycopg2.
This ensures proper transaction handling.
"""

import psycopg2
import random
from datetime import datetime

# Connection details
NEON_CONN_STR = "postgresql://neondb_owner:npg_oMzlU85mfZCI@ep-cold-frog-a1jh032w-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Business segments
SEGMENTS = ['Food Delivery', 'Grocery Delivery']

# Time periods
PERIODS = ['Q1 2023', 'Q2 2023', 'Q3 2023', 'Q4 2023']

# Base metric ranges
BASE_METRICS = {
    'orders': {
        'Food Delivery': [95, 110, 120, 150],
        'Grocery Delivery': [42, 50, 58, 72],
    },
    'aov': {
        'Food Delivery': [298, 312, 315, 335],
        'Grocery Delivery': [245, 258, 262, 278],
    },
    'commission_rate': {
        'Food Delivery': [18.5, 19.0, 19.5, 20.0],
        'Grocery Delivery': [16.0, 16.5, 17.0, 17.5],
    },
    'delivery_charges': {
        'Food Delivery': [1.20, 1.30, 1.45, 1.60],
        'Grocery Delivery': [2.10, 2.25, 2.35, 2.50],
    },
    'discounts': {
        'Food Delivery': [3.50, 3.60, 3.80, 4.20],
        'Grocery Delivery': [2.80, 2.95, 3.10, 3.40],
    },
    'marketing_spend': {
        'Food Delivery': [2.80, 3.00, 3.20, 3.80],
        'Grocery Delivery': [1.50, 1.80, 2.00, 2.40],
    },
    'new_users': {
        'Food Delivery': [8.0, 9.0, 10.5, 13.0],
        'Grocery Delivery': [5.5, 6.5, 7.5, 9.0],
    },
    'active_users': {
        'Food Delivery': [42.0, 44.0, 46.0, 52.0],
        'Grocery Delivery': [28.0, 32.0, 36.0, 42.0],
    },
    'basket_size': {
        'Food Delivery': [3.1, 3.2, 3.5, 3.8],
        'Grocery Delivery': [4.2, 4.3, 4.4, 4.6],
    },
    'restaurant_partners': {
        'Food Delivery': [200.0, 220.0, 240.0, 280.0],
        'Grocery Delivery': [120.0, 135.0, 150.0, 175.0],
    },
    'pricing_index': {
        'Food Delivery': [100.0, 102.0, 105.0, 108.0],
        'Grocery Delivery': [100.0, 101.0, 103.0, 105.0],
    },
}

def compute_derived_metrics(base_values):
    """Compute derived metrics from base metrics"""
    orders = base_values.get('orders', 0)
    aov = base_values.get('aov', 0)
    commission_rate = base_values.get('commission_rate', 0)
    delivery_charges = base_values.get('delivery_charges', 0)
    discounts = base_values.get('discounts', 0)
    marketing_spend = base_values.get('marketing_spend', 0)
    new_users = base_values.get('new_users', 0)
    active_users = base_values.get('active_users', 0)
    
    # Compute derived metrics using formulas
    gmv = orders * aov / 1000.0  # GMV in billions
    revenue = gmv * commission_rate / 100.0 + delivery_charges - discounts
    take_rate = (revenue / gmv * 100.0) if gmv > 0 else 0
    arpu = (revenue / active_users * 1000.0) if active_users > 0 else 0
    order_frequency = (orders / active_users) if active_users > 0 else 0
    cac = (marketing_spend / new_users * 1000.0) if new_users > 0 else 0
    
    return {
        'gmv': round(gmv, 2),
        'revenue': round(revenue, 2),
        'take_rate': round(take_rate, 2),
        'arpu': round(arpu, 2),
        'order_frequency': round(order_frequency, 2),
        'cac': round(cac, 2),
    }

def main():
    print("Connecting to Neon with psycopg2...")
    
    try:
        # Connect
        conn = psycopg2.connect(NEON_CONN_STR)
        cur = conn.cursor()
        conn.autocommit = False  # Explicit transaction control
        
        print("✓ Connected\n")
        
        # Clear
        print("🧹 Clearing existing time_series_data...")
        cur.execute("DELETE FROM time_series_data")
        conn.commit()
        print("✓ Cleared\n")
        
        # Insert BASE + DERIVED metrics
        print("📊 Inserting metric data...\n")
        total_inserted = 0
        
        for period_idx, period in enumerate(PERIODS):
            print(f"  {period}")
            for segment in SEGMENTS:
                # Collect base values for this period/segment
                base_values = {}
                for metric_name, values_by_segment in BASE_METRICS.items():
                    if segment in values_by_segment:
                        value = values_by_segment[segment][period_idx]
                        variance = value * random.uniform(-0.02, 0.02)
                        value = round(value + variance, 2)
                        base_values[metric_name] = value
                
                # Insert base metrics
                for metric_name, value in base_values.items():
                    cur.execute(
                        """INSERT INTO time_series_data 
                           (metric_name, period, segment, value, is_computed, created_at)
                           VALUES (%s, %s, %s, %s, false, NOW())""",
                        (metric_name, period, segment, value)
                    )
                    total_inserted += 1
                
                # Compute and insert derived metrics
                derived = compute_derived_metrics(base_values)
                for metric_name, value in derived.items():
                    cur.execute(
                        """INSERT INTO time_series_data 
                           (metric_name, period, segment, value, is_computed, created_at)
                           VALUES (%s, %s, %s, %s, true, NOW())""",
                        (metric_name, period, segment, value)
                    )
                    total_inserted += 1
            
            # Commit after each period
            conn.commit()
            print(f"    ✓ {segment} - {len(BASE_METRICS)} base + 6 derived metrics")
        
        print(f"\n✅ Successfully inserted {total_inserted} rows (11 base + 6 derived metrics across 2 segments & 4 periods)\n")
        
        # Verify
        cur.execute("SELECT COUNT(*) FROM time_series_data")
        count = cur.fetchone()[0]
        print(f"✓ Verification: {count} rows now in table\n")
        
        # Show sample
        cur.execute("""SELECT metric_name, period, segment, value 
                       FROM time_series_data 
                       ORDER BY period, metric_name 
                       LIMIT 5""")
        print("Sample data:")
        for row in cur.fetchall():
            print(f"  {row[0]:20} | {row[1]:10} | {row[2]:20} | {row[3]:.2f}")
        
        cur.close()
        conn.close()
        print("\n✓ Done")
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
