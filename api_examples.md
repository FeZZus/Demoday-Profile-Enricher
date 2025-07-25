# API Examples

This file contains practical examples for testing the Airtable LinkedIn URL Extractor API using various tools.

## curl Examples

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/health" \
  -H "accept: application/json"
```

### 2. Start Basic Extraction Job
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "linkedin_fields": ["4. CEO LinkedIn"],
      "event_filter": "S25",
      "top_100_filter": true,
      "output_prefix": "S25Top100_API"
    }
  }'
```

### 3. Start Custom Extraction Job
```bash
curl -X POST "http://localhost:8000/extract" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "linkedin_fields": ["4. CEO LinkedIn", "Alternative LinkedIn"],
      "event_filter": "S25",
      "top_100_filter": false,
      "output_prefix": "S25_All"
    },
    "job_id": "my_custom_job_123"
  }'
```

### 4. Check Job Status
```bash
# Replace JOB_ID with actual job ID from step 2
curl -X GET "http://localhost:8000/status/JOB_ID" \
  -H "accept: application/json"
```

### 5. Get Job Results
```bash
# Replace JOB_ID with actual job ID from step 2
curl -X GET "http://localhost:8000/results/JOB_ID" \
  -H "accept: application/json"
```

### 6. List All Jobs
```bash
curl -X GET "http://localhost:8000/jobs" \
  -H "accept: application/json"
```

### 7. Delete a Job
```bash
# Replace JOB_ID with actual job ID
curl -X DELETE "http://localhost:8000/jobs/JOB_ID" \
  -H "accept: application/json"
```

## PowerShell Examples (Windows)

### 1. Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
```

### 2. Start Extraction Job
```powershell
$body = @{
    config = @{
        linkedin_fields = @("4. CEO LinkedIn")
        event_filter = "S25"
        top_100_filter = $true
        output_prefix = "S25Top100_PS"
    }
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:8000/extract" -Method Post -Body $body -ContentType "application/json"
$jobId = $response.job_id
Write-Host "Job ID: $jobId"
```

### 3. Monitor Job Progress
```powershell
# Replace $jobId with actual job ID
do {
    $status = Invoke-RestMethod -Uri "http://localhost:8000/status/$jobId" -Method Get
    Write-Host "Status: $($status.status)"
    if ($status.progress -and $status.progress.percentage) {
        Write-Host "Progress: $($status.progress.percentage)%"
    }
    Start-Sleep 5
} while ($status.status -eq "running")

if ($status.status -eq "completed") {
    $results = Invoke-RestMethod -Uri "http://localhost:8000/results/$jobId" -Method Get
    Write-Host "Extraction completed: $($results.valid_urls) LinkedIn URLs found"
}
```

## Python Requests Examples

### 1. Complete Workflow
```python
import requests
import time
import json

# API base URL
BASE_URL = "http://localhost:8000"

# 1. Health check
health = requests.get(f"{BASE_URL}/health").json()
print(f"API Health: {health['status']}")

# 2. Start extraction
config = {
    "config": {
        "linkedin_fields": ["4. CEO LinkedIn"],
        "event_filter": "S25",
        "top_100_filter": True,
        "output_prefix": "S25Top100_Python"
    }
}

response = requests.post(f"{BASE_URL}/extract", json=config)
job_id = response.json()["job_id"]
print(f"Started job: {job_id}")

# 3. Monitor progress
while True:
    status = requests.get(f"{BASE_URL}/status/{job_id}").json()
    print(f"Status: {status['status']}")
    
    if status.get('progress', {}).get('percentage'):
        print(f"Progress: {status['progress']['percentage']}%")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(5)

# 4. Get results
if status['status'] == 'completed':
    results = requests.get(f"{BASE_URL}/results/{job_id}").json()
    print(f"Results: {results['valid_urls']} URLs extracted")
    
    # Save to file
    with open('api_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("Results saved to api_results.json")
```

### 2. Batch Processing Multiple Jobs
```python
import requests
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8000"

def start_extraction(config_name, config):
    """Start an extraction job."""
    response = requests.post(f"{BASE_URL}/extract", json={"config": config})
    job_id = response.json()["job_id"]
    print(f"Started {config_name}: {job_id}")
    return job_id

def wait_for_job(job_id):
    """Wait for a job to complete."""
    while True:
        status = requests.get(f"{BASE_URL}/status/{job_id}").json()
        if status['status'] in ['completed', 'failed']:
            return status
        time.sleep(2)

# Define multiple extraction configurations
configs = {
    "S25_Top100": {
        "linkedin_fields": ["4. CEO LinkedIn"],
        "event_filter": "S25",
        "top_100_filter": True,
        "output_prefix": "S25Top100"
    },
    "S25_All": {
        "linkedin_fields": ["4. CEO LinkedIn"],
        "event_filter": "S25",
        "top_100_filter": False,
        "output_prefix": "S25_All"
    }
}

# Start all jobs
job_ids = {}
for name, config in configs.items():
    job_ids[name] = start_extraction(name, config)

# Wait for all jobs to complete
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {name: executor.submit(wait_for_job, job_id) 
              for name, job_id in job_ids.items()}
    
    for name, future in futures.items():
        status = future.result()
        if status['status'] == 'completed':
            results = requests.get(f"{BASE_URL}/results/{job_ids[name]}").json()
            print(f"{name}: {results['valid_urls']} URLs extracted")
        else:
            print(f"{name}: Failed - {status.get('error', 'Unknown error')}")
```

## JavaScript/Node.js Examples

### 1. Using fetch API
```javascript
// Start extraction job
async function startExtraction() {
    const config = {
        config: {
            linkedin_fields: ["4. CEO LinkedIn"],
            event_filter: "S25",
            top_100_filter: true,
            output_prefix: "S25Top100_JS"
        }
    };
    
    const response = await fetch("http://localhost:8000/extract", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(config)
    });
    
    const result = await response.json();
    console.log("Job started:", result.job_id);
    return result.job_id;
}

// Monitor job progress
async function monitorJob(jobId) {
    while (true) {
        const response = await fetch(`http://localhost:8000/status/${jobId}`);
        const status = await response.json();
        
        console.log(`Status: ${status.status}`);
        if (status.progress?.percentage) {
            console.log(`Progress: ${status.progress.percentage}%`);
        }
        
        if (status.status === 'completed' || status.status === 'failed') {
            return status;
        }
        
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

// Main execution
(async () => {
    try {
        const jobId = await startExtraction();
        const finalStatus = await monitorJob(jobId);
        
        if (finalStatus.status === 'completed') {
            const resultsResponse = await fetch(`http://localhost:8000/results/${jobId}`);
            const results = await resultsResponse.json();
            console.log(`Extraction completed: ${results.valid_urls} URLs found`);
        }
    } catch (error) {
        console.error("Error:", error);
    }
})();
```

## Testing Script

Create a file called `test_api.py`:

```python
#!/usr/bin/env python3
"""
Quick API test script
"""
import requests
import sys

def test_api():
    base_url = "http://localhost:8000"
    
    try:
        # Test health endpoint
        health = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health check: {health.json()['status']}")
        
        # Test starting a small job
        config = {
            "config": {
                "linkedin_fields": ["4. CEO LinkedIn"],
                "event_filter": "S25",
                "top_100_filter": True,
                "output_prefix": "API_Test"
            }
        }
        
        job_response = requests.post(f"{base_url}/extract", json=config)
        job_id = job_response.json()["job_id"]
        print(f"✅ Job started: {job_id}")
        
        # Check job status
        status = requests.get(f"{base_url}/status/{job_id}")
        print(f"✅ Job status: {status.json()['status']}")
        
        print("🎉 API is working correctly!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_api()
```

Run with: `python test_api.py` 