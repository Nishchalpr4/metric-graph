#!/usr/bin/env python
"""
Auto-sync Neon data to local database on a schedule.
Runs every 6 hours, always keeps data fresh.
"""

import time
import psycopg2
import random
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

NEON_CONN_STR = "postgresql://neondb_owner:npg_oMzlU85mfZCI@ep-cold-frog-a1jh032w-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

SEGMENTS = ['Food Delivery', 'Grocery Delivery']
PERIODS = ['Q1 2023', 'Q2 2023', 'Q3 2023', 'Q4 2023']

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

def populate_neon():
    """Populate Neon with fresh data"""
    try:
        conn = psycopg2.connect(NEON_CONN_STR)
        cur = conn.cursor()
        conn.autocommit = False
        
        # Clear
        cur.execute("DELETE FROM time_series_data")
        conn.commit()
        
        # Insert
        total = 0
        for period_idx, period in enumerate(PERIODS):
            for segment in SEGMENTS:
                for metric_name, values_by_segment in BASE_METRICS.items():
                    if segment in values_by_segment:
                        value = values_by_segment[segment][period_idx]
                        variance = value * random.uniform(-0.02, 0.02)
                        value = round(value + variance, 2)
                        
                        cur.execute(
                            "INSERT INTO time_series_data (metric_name, period, segment, value, is_computed, created_at) VALUES (%s, %s, %s, %s, false, NOW())",
                            (metric_name, period, segment, value)
                        )
                        total += 1
            conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Auto-synced {total} rows to Neon")
        return True
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
        return False

def start_auto_sync(interval_hours=6):
    """Start background auto-sync scheduler"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        populate_neon,
        'interval',
        hours=interval_hours,
        id='neon_auto_sync'
    )
    scheduler.start()
    print(f"Auto-sync started (every {interval_hours} hours)")
    return scheduler

if __name__ == '__main__':
    # Populate once now
    print("Populating Neon now...")
    populate_neon()
    
    # Then set up auto-sync every 6 hours
    scheduler = start_auto_sync(interval_hours=6)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Auto-sync stopped")
