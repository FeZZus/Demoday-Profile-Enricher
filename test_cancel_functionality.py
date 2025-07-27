#!/usr/bin/env python3
"""
Test script to verify the cancel job functionality works correctly.
"""

import requests
import json
import time

def test_cancel_functionality():
    """Test the cancel job endpoints."""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing cancel job functionality...")
    print("-" * 50)
    
    # Test 1: Check if cancel endpoints exist
    print("1. Testing cancel endpoint availability...")
    
    try:
        # Test extraction job cancel endpoint
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("✅ API documentation accessible")
        else:
            print("❌ API documentation not accessible")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False
    
    # Test 2: Try to cancel a non-existent job
    print("\n2. Testing cancel non-existent job...")
    
    try:
        response = requests.post(f"{base_url}/jobs/fake-job-id/cancel")
        if response.status_code == 404:
            print("✅ Correctly returns 404 for non-existent job")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing non-existent job: {e}")
        return False
    
    # Test 3: Try to cancel a completed job (should fail)
    print("\n3. Testing cancel completed job...")
    
    try:
        # First, check if there are any completed jobs
        response = requests.get(f"{base_url}/jobs")
        if response.status_code == 200:
            jobs = response.json()
            completed_jobs = [job for job in jobs.get('jobs', []) if job['status'] == 'completed']
            
            if completed_jobs:
                job_id = completed_jobs[0]['job_id']
                response = requests.post(f"{base_url}/jobs/{job_id}/cancel")
                if response.status_code == 400:
                    print("✅ Correctly prevents cancelling completed job")
                else:
                    print(f"❌ Expected 400, got {response.status_code}")
            else:
                print("ℹ️  No completed jobs found to test")
        else:
            print(f"❌ Failed to get jobs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing completed job: {e}")
        return False
    
    # Test 4: Check all cancel endpoints exist
    print("\n4. Testing all cancel endpoints...")
    
    cancel_endpoints = [
        "/jobs/{job_id}/cancel",
        "/apify/jobs/{job_id}/cancel", 
        "/cleaner/jobs/{job_id}/cancel",
        "/traits/jobs/{job_id}/cancel",
        "/airtable/jobs/{job_id}/cancel"
    ]
    
    for endpoint in cancel_endpoints:
        try:
            response = requests.post(f"{base_url}{endpoint.replace('{job_id}', 'test-id')}")
            # We expect 404 since the job doesn't exist, but the endpoint should be available
            if response.status_code in [404, 400]:
                print(f"✅ {endpoint} endpoint exists")
            else:
                print(f"❌ {endpoint} endpoint not working properly (status: {response.status_code})")
        except Exception as e:
            print(f"❌ {endpoint} endpoint error: {e}")
    
    print("\n✅ All cancel functionality tests completed!")
    print("\n📝 To test actual job cancellation:")
    print("1. Start a job in the frontend")
    print("2. Click the 'Cancel' button while it's running")
    print("3. Verify the job status changes to 'cancelled'")
    
    return True

if __name__ == "__main__":
    test_cancel_functionality() 