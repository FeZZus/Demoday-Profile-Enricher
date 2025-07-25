# Airtable LinkedIn URL Extractor API

A FastAPI backend for extracting LinkedIn URLs from Airtable records with progress tracking, background job processing, and configurable filters.

## Features

- ✅ **Asynchronous Processing**: Background job execution with real-time progress tracking
- ✅ **Configurable Filters**: Extract data based on events, top 100 status, and custom fields
- ✅ **Progress Tracking**: Monitor extraction progress with percentage and status updates
- ✅ **Job Management**: Start, stop, monitor, and manage multiple extraction jobs
- ✅ **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- ✅ **Error Handling**: Comprehensive error handling and status reporting
- ✅ **File Output**: Saves results to JSON files with configurable naming

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file:

```env
AIRTABLE_API_KEY=your_airtable_api_key_here
```

### 3. Start the API Server

#### Option A: Using the start script
```bash
python start_api.py
```

#### Option B: Using uvicorn directly
```bash
uvicorn airtable_api:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access the API

- **API Server**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### 🏠 Root
- **GET** `/` - API information and available endpoints

### 🚀 Extraction Management
- **POST** `/extract` - Start a new extraction job
- **GET** `/status/{job_id}` - Get job status and progress
- **GET** `/results/{job_id}` - Get completed job results
- **GET** `/jobs` - List all jobs
- **DELETE** `/jobs/{job_id}` - Delete a job

### 🏥 Health & Monitoring
- **GET** `/health` - Health check and system status

## Usage Examples

### Starting an Extraction Job

```python
import requests

# Basic extraction (S25 Top 100)
response = requests.post("http://localhost:8000/extract", json={
    "config": {
        "linkedin_fields": ["4. CEO LinkedIn"],
        "event_filter": "S25",
        "top_100_filter": True,
        "output_prefix": "S25Top100_API"
    }
})

job_id = response.json()["job_id"]
print(f"Job started: {job_id}")
```

### Custom Extraction Configuration

```python
# Extract all S25 records (not just top 100)
response = requests.post("http://localhost:8000/extract", json={
    "config": {
        "linkedin_fields": ["4. CEO LinkedIn", "Alternative LinkedIn Field"],
        "event_filter": "S25",
        "top_100_filter": False,
        "output_prefix": "S25_All"
    }
})
```

### Monitoring Job Progress

```python
# Check job status
status = requests.get(f"http://localhost:8000/status/{job_id}").json()
print(f"Status: {status['status']}")
print(f"Progress: {status['progress']}")

# Get results when completed
if status['status'] == 'completed':
    results = requests.get(f"http://localhost:8000/results/{job_id}").json()
    print(f"Found {results['valid_urls']} LinkedIn URLs")
```

### Using the Python Client

```python
from api_client_example import AirtableAPIClient

client = AirtableAPIClient()

# Start extraction
job = client.start_extraction(
    event_filter="S25",
    top_100_filter=True,
    output_prefix="MyExtraction"
)

# Wait for completion with progress updates
results = client.wait_for_completion(job['job_id'], timeout=600)
print(f"Extraction complete: {results['valid_urls']} URLs found")
```

## Configuration Options

### ExtractionConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `linkedin_fields` | List[str] | `["4. CEO LinkedIn"]` | Airtable field names to check for LinkedIn URLs |
| `event_filter` | str | `"S25"` | Filter records by event (e.g., "S25", "W24") |
| `top_100_filter` | bool | `true` | Only process "Top 100" records |
| `output_prefix` | str | `"S25Top100"` | Prefix for output JSON files |

### Server Configuration

```bash
# Development mode (auto-reload enabled)
python start_api.py --host 0.0.0.0 --port 8000

# Production mode (no auto-reload)
python start_api.py --host 0.0.0.0 --port 8000 --no-reload --log-level warning

# Custom configuration
python start_api.py --host 127.0.0.1 --port 9000 --log-level debug
```

## Job Status Flow

```
queued → running → completed
   ↓        ↓         ↓
   └─────→ failed ←──┘
```

- **queued**: Job is waiting to start
- **running**: Extraction is in progress
- **completed**: Job finished successfully
- **failed**: Job encountered an error

## Output Files

Each extraction job creates three JSON files in the `airtable-extractions/` directory:

1. **`{prefix}airtable_url_mapping.json`** - Maps LinkedIn URLs to Airtable record IDs
2. **`{prefix}linkedin_urls_for_apify.json`** - Clean list of LinkedIn URLs for further processing
3. **`{prefix}airtable_extraction_results.json`** - Complete extraction results with metadata

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid job ID or incomplete jobs
- **404 Not Found**: Job not found
- **409 Conflict**: Job ID already exists
- **500 Internal Server Error**: Server or extraction errors

Example error response:
```json
{
    "detail": "Job 'invalid_job_id' not found"
}
```

## Real-time Progress Tracking

Monitor extraction progress with detailed updates:

```json
{
    "job_id": "job_20241201_143022_a1b2c3d4",
    "status": "running",
    "progress": {
        "current": 45,
        "total": 100,
        "percentage": 45.0,
        "message": "Processing record 45",
        "timestamp": "2024-12-01T14:32:15.123456"
    }
}
```

## Security Considerations

- Store `AIRTABLE_API_KEY` securely in environment variables
- Consider adding authentication for production deployments
- Use HTTPS in production environments
- Implement rate limiting for high-traffic scenarios

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when available)
pytest tests/
```

### Local Development

```bash
# Install in development mode
pip install -e .

# Start with auto-reload
python start_api.py

# View logs
tail -f logs/api.log
```

## Troubleshooting

### Common Issues

1. **"AIRTABLE_API_KEY environment variable not set"**
   - Create a `.env` file with your Airtable API key

2. **"Missing dependencies" error**
   - Run `pip install -r requirements.txt`

3. **Connection errors**
   - Check if the server is running on the correct port
   - Verify firewall settings

4. **Extraction failures**
   - Verify Airtable base and table IDs in `airtable_extractor.py`
   - Check Airtable API permissions

### Support

For issues or questions:
1. Check the interactive API docs at `/docs`
2. Review server logs for detailed error messages
3. Verify environment configuration

## License

This project is part of the Onstage Profile Enricher system. 