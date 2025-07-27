#!/usr/bin/env python3
"""
Test script to verify that the async cancel functionality works properly.
This script will:
1. Start a long-running job
2. Try to cancel it immediately
3. Verify that the cancel request is processed quickly
"""

import asyncio
import requests
import time
import json

# API base URL
BASE_URL = "http://localhost:8000"

def test_cancel_functionality():
    """Test the cancel functionality with a long-running job."""
    
    print("🧪 Testing Async Cancel Functionality")
    print("=" * 50)
    
    # Step 1: Start a long-running job
    print("1. Starting a long-running extraction job...")
    
    extraction_config = {
        "linkedin_fields": ["4. CEO LinkedIn"],
        "event_filter": "S25",
        "top_100_filter": True,
        "output_prefix": "test_cancel"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/extract",
            json={"config": extraction_config},
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start job: {response.status_code}")
            print(response.text)
            return False
            
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✅ Job started successfully: {job_id}")
        
    except Exception as e:
        print(f"❌ Failed to start job: {e}")
        return False
    
    # Step 2: Wait a moment for the job to start
    print("2. Waiting for job to start...")
    time.sleep(2)
    
    # Step 3: Check job status
    print("3. Checking job status...")
    try:
        status_response = requests.get(f"{BASE_URL}/status/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"📊 Job status: {status_data['status']}")
        else:
            print(f"❌ Failed to get job status: {status_response.status_code}")
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    # Step 4: Try to cancel the job
    print("4. Attempting to cancel the job...")
    start_time = time.time()
    
    try:
        cancel_response = requests.post(f"{BASE_URL}/jobs/{job_id}/cancel")
        cancel_time = time.time() - start_time
        
        if cancel_response.status_code == 200:
            print(f"✅ Cancel request processed in {cancel_time:.2f} seconds")
            cancel_data = cancel_response.json()
            print(f"📊 Cancel response: {cancel_data}")
        else:
            print(f"❌ Cancel request failed: {cancel_response.status_code}")
            print(cancel_response.text)
            
    except Exception as e:
        print(f"❌ Error cancelling job: {e}")
    
    # Step 5: Check final status
    print("5. Checking final job status...")
    time.sleep(1)  # Give it a moment to process
    
    try:
        final_status_response = requests.get(f"{BASE_URL}/status/{job_id}")
        if final_status_response.status_code == 200:
            final_status = final_status_response.json()
            print(f"📊 Final job status: {final_status['status']}")
            
            if final_status['status'] == 'cancelled':
                print("✅ Job was successfully cancelled!")
                return True
            else:
                print(f"⚠️ Job status is {final_status['status']} (expected 'cancelled')")
                return False
        else:
            print(f"❌ Failed to get final status: {final_status_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking final status: {e}")
        return False

def test_cancel_all_jobs():
    """Test the cancel all jobs functionality."""
    
    print("\n🧪 Testing Cancel All Jobs Functionality")
    print("=" * 50)
    
    # Step 1: Start multiple jobs
    print("1. Starting multiple jobs...")
    job_ids = []
    
    for i in range(3):
        extraction_config = {
            "linkedin_fields": ["4. CEO LinkedIn"],
            "event_filter": "S25",
            "top_100_filter": True,
            "output_prefix": f"test_cancel_all_{i}"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/extract",
                json={"config": extraction_config},
                timeout=10
            )
            
            if response.status_code == 200:
                job_id = response.json()["job_id"]
                job_ids.append(job_id)
                print(f"✅ Started job {i+1}: {job_id}")
            else:
                print(f"❌ Failed to start job {i+1}")
                
        except Exception as e:
            print(f"❌ Error starting job {i+1}: {e}")
    
    if not job_ids:
        print("❌ No jobs were started successfully")
        return False
    
    # Step 2: Wait for jobs to start
    print("2. Waiting for jobs to start...")
    time.sleep(3)
    
    # Step 3: Try to cancel all jobs via the frontend API
    print("3. Attempting to cancel all jobs...")
    start_time = time.time()
    
    try:
        # This would normally be called from the frontend
        # For testing, we'll call the individual cancel endpoints
        cancelled_count = 0
        
        for job_id in job_ids:
            try:
                cancel_response = requests.post(f"{BASE_URL}/jobs/{job_id}/cancel")
                if cancel_response.status_code == 200:
                    cancelled_count += 1
                    print(f"✅ Cancelled job: {job_id}")
                else:
                    print(f"❌ Failed to cancel job {job_id}: {cancel_response.status_code}")
            except Exception as e:
                print(f"❌ Error cancelling job {job_id}: {e}")
        
        cancel_time = time.time() - start_time
        print(f"📊 Cancelled {cancelled_count}/{len(job_ids)} jobs in {cancel_time:.2f} seconds")
        
        return cancelled_count > 0
        
    except Exception as e:
        print(f"❌ Error in cancel all test: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Cancel Functionality Tests")
    print("Make sure the backend is running on http://localhost:8000")
    print()
    
    # Test 1: Single job cancellation
    success1 = test_cancel_functionality()
    
    # Test 2: Cancel all jobs
    success2 = test_cancel_all_jobs()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Single job cancellation: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Cancel all jobs: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! The async cancel functionality is working.")
    else:
        print("\n⚠️ Some tests failed. Check the backend logs for more details.") 