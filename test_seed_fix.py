#!/usr/bin/env python3
"""
Test script to verify /api/seed is now working correctly.
Run this to check if the fix is deployed and data is being synced.

Usage:
    python test_seed_fix.py http://127.0.0.1:8000
    # or
    python test_seed_fix.py https://your-render-domain.onrender.com
"""

import sys
import requests
import json
from time import time

def test_seed_endpoint(base_url):
    """Test the /api/seed endpoint and display results."""
    
    url = f"{base_url}/api/seed"
    
    print("=" * 80)
    print("Testing /api/seed Endpoint")
    print("=" * 80)
    print(f"URL: {url}\n")
    
    try:
        print("Calling /api/seed endpoint...")
        start = time()
        response = requests.post(url, timeout=30)
        elapsed = time() - start
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f}s\n")
        
        if response.status_code != 200:
            print(f"❌ ERROR: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        print("Response JSON:")
        print(json.dumps(data, indent=2))
        print()
        
        # Check for expected fields
        if "data" not in data:
            print("❌ ERROR: Missing 'data' field in response")
            return False
        
        counts = data["data"]
        
        # Verify counts
        print("=" * 80)
        print("Data Validation")
        print("=" * 80)
        
        filings = counts.get("filings", 0)
        periods = counts.get("periods", 0)
        companies = counts.get("companies", 0)
        metrics = counts.get("metrics_loaded", 0)
        
        print(f"Filings:        {filings:>6}")
        print(f"Periods:        {periods:>6}")
        print(f"Companies:      {companies:>6}")
        print(f"Metrics Loaded: {metrics:>6}")
        print()
        
        # Check if fix is working
        if filings == 0 and periods == 0 and companies == 0:
            print("❌ STILL BROKEN: All data counts are 0")
            print("   The seed endpoint is not syncing canonical data.")
            print("   Make sure you deployed the latest fix to Render.")
            return False
        
        if companies > 0:
            print("✅ SUCCESS: Companies are being synced!")
        
        if periods > 0:
            print("✅ SUCCESS: Periods are being found!")
        
        if filings > 0:
            print("✅ SUCCESS: Filings are being found!")
        
        print()
        print("=" * 80)
        
        # Check sync details
        if "sync_details" in counts:
            sync = counts["sync_details"]
            print("Sync Details:")
            print(f"  Companies Synced: {sync.get('companies_synced', 0)}")
            print(f"  Metrics Synced:   {sync.get('metrics_synced', 0)}")
            print()
        
        # Overall status
        if companies > 0 and periods > 0:
            print("✅ FULLY FIXED: Database seeding is working correctly!")
            print("   You can now use /api/query to ask questions about your data.")
            return True
        else:
            print("⚠️  PARTIAL: Some data is present but not all categories.")
            print("   Check database population status.")
            return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR: Could not connect to {base_url}")
        print(f"   Make sure the API is running.")
        print(f"   Connection Error: {e}")
        return False
    
    except requests.exceptions.Timeout:
        print(f"❌ ERROR: Request timed out after 30 seconds")
        print(f"   The seed endpoint may be taking too long.")
        return False
    
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_seed_fix.py <base_url>")
        print()
        print("Examples:")
        print("  python test_seed_fix.py http://127.0.0.1:8000")
        print("  python test_seed_fix.py https://your-render-domain.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip("/")
    success = test_seed_endpoint(base_url)
    sys.exit(0 if success else 1)
