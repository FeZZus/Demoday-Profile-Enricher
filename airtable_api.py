"""

DONT GET THIS AT ALL: https://chatgpt.com/c/6880147d-11c4-8012-ad88-f3d9c4474745


FastAPI Backend for Airtable LinkedIn URL Extraction

This API provides endpoints to:
- Trigger LinkedIn URL extraction from Airtable
- Check extraction status and progress
- Retrieve extraction results
- Configure extraction parameters

Usage:
    uvicorn airtable_api:app --reload --host 0.0.0.0 --port 8000
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from airtable_extractor import AirtableLinkedInExtractor
from apify_requester import process_linkedin_profiles_with_resume, load_linkedin_urls
from data_cleaner import LinkedInDataProcessor
from trait_extractor import LinkedInTraitExtractor
from airtable_updater import AirtableTraitUpdater

# Initialize FastAPI app
app = FastAPI(
    title="Airtable LinkedIn URL Extractor API",
    description="API for extracting LinkedIn URLs from Airtable records and processing them through Apify",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for tracking extraction jobs
extraction_jobs: Dict[str, Dict[str, Any]] = {}
apify_jobs: Dict[str, Dict[str, Any]] = {}
data_cleaner_jobs: Dict[str, Dict[str, Any]] = {}
trait_extractor_jobs: Dict[str, Dict[str, Any]] = {}
airtable_updater_jobs: Dict[str, Dict[str, Any]] = {}

# Terminal logs storage
terminal_logs: List[Dict[str, Any]] = []
MAX_LOGS = 1000  # Keep last 1000 log entries

def add_terminal_log(level: str, message: str):
    """Add a log entry to the terminal logs."""
    log_entry = {
        "id": len(terminal_logs) + 1,
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    }
    terminal_logs.append(log_entry)
    
    # Keep only the last MAX_LOGS entries
    if len(terminal_logs) > MAX_LOGS:
        terminal_logs.pop(0)

# Pydantic models for request/response validation
# We use these in the post/get requests to tell the api what format the data is being sent in
class ExtractionConfig(BaseModel):
    """Configuration for LinkedIn URL extraction."""
    linkedin_fields: List[str] = Field(
        default=["4. CEO LinkedIn"],
        description="List of Airtable field names to check for LinkedIn URLs"
    )
    event_filter: Optional[str] = Field(
        default="S25",
        description="Event filter (e.g., 'S25')"
    )
    # THIS IS YAAAAAP
    top_100_filter: Optional[bool] = Field(
        default=True,
        description="Filter for Top 100 records only"
    )
    output_prefix: str = Field(
        default="test",
        description="Prefix for output filenames"
    )

# Whenever a client sends an endpoint with data as {"config": ..., "job_id": ..}, fast api:
    # Parses it into a Extraction request instance,
    # The config field in itself is the ExtractionConfif Data model 
        # Config must exist, but if not provided its default to extraction config (Field(default_factory=ExtractionConfig))
        # job_id doesn't have to exist, and if no value is provided, then it's set to None (Field(default = None))
        # job id is optional. 

# the = ... is just the default value if nothing is provided
class ExtractionRequest(BaseModel):
    """model for starting whenever an airtable extraciton is asked for."""
    config: ExtractionConfig = Field(default_factory=ExtractionConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class ExtractionStatus(BaseModel):
    """Status model for extraction jobs."""
    job_id: str
    status: str  # "running", "completed", "failed", "not_found"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ExtractionResults(BaseModel):
    """Results model for completed extractions."""
    job_id: str
    total_records: int
    valid_urls: int
    invalid_urls: int
    missing_urls: int
    success_rate: float
    files_created: List[str]
    url_to_record_mapping: Dict[str, str]
    urls_for_apify: List[str]

class ApifyConfig(BaseModel):
    """Configuration for Apify LinkedIn profile processing."""
    urls_file: str = Field(
        default="airtable-extractions/S25Top100linkedin_urls_for_apify.json",
        description="Path to the JSON file containing LinkedIn URLs"
    )
    output_file: str = Field(
        default="apify-profile-data/S25Top100linkedin_profile_data.json",
        description="Path to save the processed profile data"
    )
    batch_size: int = Field(
        default=50,
        description="Number of URLs to process in each batch"
    )
    test_mode: bool = Field(
        default=False,
        description="Run in test mode with limited URLs"
    )
    test_num_urls: int = Field(
        default=10,
        description="Number of URLs to process in test mode"
    )

class ApifyRequest(BaseModel):
    """Request model for starting an Apify processing job."""
    config: ApifyConfig = Field(default_factory=ApifyConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class ApifyStatus(BaseModel):
    """Status model for Apify processing jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DataCleanerConfig(BaseModel):
    """Configuration for data cleaning jobs."""
    input_file: str = Field(
        default="apify-profile-data/S25Top100linkedin_profile_data.json",
        description="Path to the input JSON file with raw profile data"
    )
    output_file: str = Field(
        default="cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
        description="Path to save the cleaned profile data"
    )

class DataCleanerRequest(BaseModel):
    """Request model for starting a data cleaning job."""
    config: DataCleanerConfig = Field(default_factory=DataCleanerConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class DataCleanerStatus(BaseModel):
    """Status model for data cleaning jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TraitExtractorConfig(BaseModel):
    """Configuration for trait extraction jobs."""
    input_file: str = Field(
        default="cleaned-profile-data/S25Top100cleaned_linkedin_data.json",
        description="Path to the cleaned LinkedIn profiles JSON file"
    )
    output_file: str = Field(
        default="final-trait-extractions/S25Top100_comprehensive_traits.json",
        description="Path to save the extracted traits data"
    )
    max_profiles: int = Field(
        default=-1,
        description="Maximum number of profiles to process (-1 for all)"
    )
    force_reextraction: bool = Field(
        default=False,
        description="Force re-extraction of all profiles even if already processed"
    )
    delay_between_calls: float = Field(
        default=1.0,
        description="Delay between OpenAI API calls in seconds"
    )

class TraitExtractorRequest(BaseModel):
    """Request model for starting a trait extraction job."""
    config: TraitExtractorConfig = Field(default_factory=TraitExtractorConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class TraitExtractorStatus(BaseModel):
    """Status model for trait extraction jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AirtableUpdaterConfig(BaseModel):
    """Configuration for Airtable update jobs."""
    traits_file: str = Field(
        default="final-trait-extractions/S25Top100_comprehensive_traits.json",
        description="Path to the trait extraction results JSON file"
    )
    url_mapping_file: str = Field(
        default="airtable-extractions/S25Top100airtable_url_mapping.json",
        description="Path to the URL mapping JSON file"
    )
    delay_between_updates: float = Field(
        default=0.5,
        description="Delay between Airtable API calls in seconds"
    )

class AirtableUpdaterRequest(BaseModel):
    """Request model for starting an Airtable update job."""
    config: AirtableUpdaterConfig = Field(default_factory=AirtableUpdaterConfig)
    job_id: Optional[str] = Field(
        default=None,
        description="Optional custom job ID. If not provided, one will be generated."
    )

class AirtableUpdaterStatus(BaseModel):
    """Status model for Airtable update jobs."""
    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Enhanced API extractor with better progress tracking
class APIAirtableLinkedInExtractor(AirtableLinkedInExtractor):
    """Enhanced extractor with progress tracking for API use."""
    
    def __init__(self, job_id: str, progress_callback=None):
        super().__init__()
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.total_processed = 0
        
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update extraction progress with terminal output."""
        # Handle None total value
        if total is None:
            total = current  # Use current as total when no estimate is available
        
        progress_data = {
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100, 1) if total > 0 else 0,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Terminal output for real-time tracking
        print(f"[{self.job_id}] {message} - {current}/{total} ({progress_data['percentage']}%)")
        
        if self.progress_callback:
            self.progress_callback(self.job_id, progress_data)
    
    def extract_linkedin_urls_with_filters(
        self, 
        linkedin_fields: List[str] = None,
        event_filter: str = "S25",
        top_100_filter: bool = True,
        output_prefix: str = "S25Top100"
    ) -> Dict[str, Any]:
        """Enhanced extraction with custom filters and progress tracking."""
        
        if linkedin_fields is None:
            linkedin_fields = ["4. CEO LinkedIn"]
        
        print(f"\n🚀 Starting extraction for job {self.job_id}")
        print(f"📋 Filters: Event={event_filter}, Top100={top_100_filter}")
        print(f"📁 Output prefix: {output_prefix}")
        print(f"🔍 LinkedIn fields: {linkedin_fields}")
        print("-" * 60)
        
        total_records = 0
        processed_pages = 0
        
        try:
            # Single pass: process records and track progress
            print(f"📊 Processing records with filters...")
            
            for records in self.table.iterate(page_size=100):
                processed_pages += 1
                
                for record in records:
                    record_id = record['id']
                    fields = record.get('fields', {})
                    
                    # Apply filters
                    filter_conditions = {}
                    if event_filter:
                        filter_conditions['Event'] = event_filter
                    if top_100_filter is not None:
                        filter_conditions['Top 100'] = top_100_filter
                    
                    matches_filter = True
                    for filter_key, filter_value in filter_conditions.items():
                        if filter_key not in fields or fields[filter_key] != filter_value:
                            matches_filter = False
                            break
                    
                    if not matches_filter:
                        continue
                    
                    total_records += 1
                    self.total_processed += 1
                    
                    # Update progress every 10 records
                    if total_records % 10 == 0:
                        self.update_progress(
                            total_records, 
                            None,  # No estimate needed
                            f"Processing record {total_records}"
                        )
                    
                    linkedin_url = None
                    found_field = None
                    
                    # Check each potential LinkedIn field
                    for field_name in linkedin_fields:
                        if field_name in fields and fields[field_name]:
                            url_candidate = fields[field_name]
                            
                            if isinstance(url_candidate, list):
                                url_candidate = url_candidate[0] if url_candidate else None
                            
                            if isinstance(url_candidate, str) and 'linkedin.com/in' in url_candidate.lower():
                                linkedin_url = self.extract_first_valid_linkedin_url(url_candidate)
                                if linkedin_url:
                                    found_field = field_name
                                    break
                    
                    # Process the found URL
                    if linkedin_url:
                        if linkedin_url not in self.url_to_record_mapping:
                            self.url_to_record_mapping[linkedin_url] = record_id
                            self.valid_urls.append(linkedin_url)
                        else:
                            print(f"Duplicate URL: {linkedin_url}")
                    else:
                        self.missing_urls[record_id] = "No valid LinkedIn URL found in any field"
            
            # Final progress update
            self.update_progress(
                total_records, 
                total_records,
                "Extraction completed, saving results..."
            )
            
            # Save results with custom prefix
            self.save_results_with_prefix(output_prefix)
            
            return {
                'total_records': total_records,
                'valid_urls': len(self.valid_urls),
                'invalid_urls': len(self.invalid_urls),
                'missing_urls': len(self.missing_urls),
                'success_rate': (len(self.valid_urls) / total_records * 100) if total_records > 0 else 0,
                'url_to_record_mapping': self.url_to_record_mapping,
                'urls_for_apify': self.valid_urls,
                'files_created': [
                    f'airtable-extractions/{output_prefix}airtable_url_mapping.json',
                    f'airtable-extractions/{output_prefix}linkedin_urls_for_apify.json',
                    f'airtable-extractions/{output_prefix}airtable_extraction_results.json'
                ]
            }
            
        except Exception as e:
            print(f"Error during extraction: {e}")
            raise
    
    # Just saves the 3 files after processing
    def save_results_with_prefix(self, prefix: str):
        """Save results with custom filename prefix."""
        # Ensure directory exists
        Path('airtable-extractions').mkdir(exist_ok=True)
        
        # Save URL to record mapping
        with open(f'airtable-extractions/{prefix}airtable_url_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(self.url_to_record_mapping, f, indent=2, ensure_ascii=False)
        
        # Save URLs for Apify
        with open(f'airtable-extractions/{prefix}linkedin_urls_for_apify.json', 'w', encoding='utf-8') as f:
            json.dump(self.valid_urls, f, indent=2, ensure_ascii=False)
        
        # Save comprehensive results
        results = {
            'extraction_summary': {
                'total_valid_urls': len(self.valid_urls),
                'total_invalid_urls': len(self.invalid_urls),
                'total_missing_urls': len(self.missing_urls)
            },
            'url_to_record_mapping': self.url_to_record_mapping,
            'valid_urls': self.valid_urls,
            'invalid_urls': self.invalid_urls,
            'missing_url_records': self.missing_urls
        }
        
        with open(f'airtable-extractions/{prefix}airtable_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

# Helper functions
def generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

def update_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update job progress and add to terminal logs."""
    if job_id in extraction_jobs:
        extraction_jobs[job_id]["progress"] = progress_data
        
        # Add progress message to terminal logs
        if "message" in progress_data:
            add_terminal_log("INFO", f"[{job_id}] {progress_data['message']}")
            
            # Add progress details if available
            if "current" in progress_data and "total" in progress_data:
                percentage = int((progress_data["current"] / progress_data["total"]) * 100)
                add_terminal_log("INFO", f"[{job_id}] Progress: {progress_data['current']}/{progress_data['total']} ({percentage}%)")
    elif job_id in apify_jobs:
        apify_jobs[job_id]["progress"] = progress_data
    elif job_id in data_cleaner_jobs:
        data_cleaner_jobs[job_id]["progress"] = progress_data
    elif job_id in trait_extractor_jobs:
        trait_extractor_jobs[job_id]["progress"] = progress_data
    elif job_id in airtable_updater_jobs:
        airtable_updater_jobs[job_id]["progress"] = progress_data

def update_apify_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update Apify job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Apify Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in apify_jobs:
        apify_jobs[job_id]["progress"] = progress_data

def update_data_cleaner_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update data cleaner job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Data Cleaner Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in data_cleaner_jobs:
        data_cleaner_jobs[job_id]["progress"] = progress_data

def update_trait_extractor_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update trait extractor job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Trait Extractor Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in trait_extractor_jobs:
        trait_extractor_jobs[job_id]["progress"] = progress_data

def update_airtable_updater_job_progress(job_id: str, progress_data: Dict[str, Any]):
    """Update Airtable updater job progress in global state with terminal output."""
    if 'message' in progress_data:
        print(f"[{job_id}] {progress_data['message']}")
        if 'processed' in progress_data and 'total' in progress_data:
            percentage = progress_data.get('percentage', 0)
            print(f"[{job_id}] Airtable Updater Progress: {progress_data['processed']}/{progress_data['total']} ({percentage}%)")
    
    if job_id in airtable_updater_jobs:
        airtable_updater_jobs[job_id]["progress"] = progress_data

async def run_extraction_job(job_id: str, config: ExtractionConfig):
    """Run extraction job in background."""
    try:
        # Update job status to running
        extraction_jobs[job_id]["status"] = "running"
        add_terminal_log("INFO", f"🚀 Starting extraction for job {job_id}")
        add_terminal_log("INFO", f"📋 Filters: Event={config.event_filter}, Top100={config.top_100_filter}")
        add_terminal_log("INFO", f"📁 Output prefix: {config.output_prefix}")
        add_terminal_log("INFO", f"🔍 LinkedIn fields: {config.linkedin_fields}")
        add_terminal_log("INFO", "-" * 60)
        
        # Create extractor with progress callback
        extractor = APIAirtableLinkedInExtractor(job_id, update_job_progress)
        
        # Run extraction
        results = extractor.extract_linkedin_urls_with_filters(
            linkedin_fields=config.linkedin_fields,
            event_filter=config.event_filter,
            top_100_filter=config.top_100_filter,
            output_prefix=config.output_prefix
        )
        
        # Save results with prefix
        extractor.save_results_with_prefix(config.output_prefix)
        
        # Update job status to completed
        extraction_jobs[job_id]["status"] = "completed"
        extraction_jobs[job_id]["completed_at"] = datetime.now()
        extraction_jobs[job_id]["results"] = results
        
        add_terminal_log("INFO", f"✅ Extraction completed successfully for job {job_id}")
        add_terminal_log("INFO", f"📊 Results: {results['valid_urls']} valid URLs, {results['invalid_urls']} invalid URLs")
        
    except Exception as e:
        # Update job status to failed
        extraction_jobs[job_id]["status"] = "failed"
        extraction_jobs[job_id]["completed_at"] = datetime.now()
        extraction_jobs[job_id]["error"] = str(e)
        
        add_terminal_log("ERROR", f"❌ Extraction failed for job {job_id}: {str(e)}")
        print(f"Extraction job {job_id} failed: {e}")

async def run_apify_job(job_id: str, config: ApifyConfig):
    """Background task to run Apify processing job."""
    try:
        # Update job status
        apify_jobs[job_id]["status"] = "running"
        
        # Get API token from environment
        api_token = os.getenv('APIFY_API_KEY')
        if not api_token:
            raise Exception("APIFY_API_KEY environment variable not set")
        
        # Load URLs from file
        urls = load_linkedin_urls(config.urls_file)
        if not urls:
            raise Exception(f"No URLs found in {config.urls_file}")
        
        # Update progress with initial stats
        update_apify_job_progress(job_id, {
            "message": f"Loaded {len(urls)} URLs from {config.urls_file}",
            "total_urls": len(urls),
            "processed_urls": 0,
            "percentage": 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Process URLs through Apify
        if config.test_mode:
            # Test mode - process limited URLs
            test_urls = urls[:config.test_num_urls]
            results = process_linkedin_profiles_with_resume(
                api_token, 
                test_urls, 
                config.output_file, 
                config.batch_size
            )
        else:
            # Full processing mode
            results = process_linkedin_profiles_with_resume(
                api_token, 
                urls, 
                config.output_file, 
                config.batch_size
            )
        
        # Update job with results
        apify_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_urls": len(urls),
                "processed_profiles": len(results) if results else 0,
                "output_file": config.output_file,
                "test_mode": config.test_mode
            }
        })
        
    except Exception as e:
        # Update job with error
        apify_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

async def run_data_cleaner_job(job_id: str, config: DataCleanerConfig):
    """Background task to run data cleaning job."""
    try:
        # Update job status
        data_cleaner_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Starting data cleaning for {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize data processor
        processor = LinkedInDataProcessor()
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Loading profiles from {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load and process profiles
        cleaned_profiles = processor.load_and_process_file(config.input_file)
        
        # Update progress
        update_data_cleaner_job_progress(job_id, {
            "message": f"Processed {len(cleaned_profiles)} profiles, saving to {config.output_file}",
            "total_profiles": len(cleaned_profiles),
            "timestamp": datetime.now().isoformat()
        })
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(config.output_file), exist_ok=True)
        
        # Save cleaned data
        with open(config.output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_profiles, f, indent=2, ensure_ascii=False)
        
        # Update job with results
        data_cleaner_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_profiles": len(cleaned_profiles),
                "input_file": config.input_file,
                "output_file": config.output_file
            }
        })
        
    except Exception as e:
        # Update job with error
        data_cleaner_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

async def run_trait_extractor_job(job_id: str, config: TraitExtractorConfig):
    """Background task to run trait extraction job."""
    try:
        # Update job status
        trait_extractor_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_trait_extractor_job_progress(job_id, {
            "message": f"Starting trait extraction for {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize trait extractor
        extractor = LinkedInTraitExtractor()
        
        # Update progress
        update_trait_extractor_job_progress(job_id, {
            "message": f"Loading profiles from {config.input_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load profiles
        with open(config.input_file, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
        
        update_trait_extractor_job_progress(job_id, {
            "message": f"Loaded {len(profiles)} profiles, starting extraction",
            "total_profiles": len(profiles),
            "processed_profiles": 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Extract traits with progress tracking
        results = extractor.extract_traits_from_profiles(
            profiles=profiles,
            delay_between_calls=config.delay_between_calls,
            max_profiles=config.max_profiles,
            force_reextraction=config.force_reextraction,
            output_file=config.output_file
        )
        
        # Update job with results
        trait_extractor_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_profiles": len(profiles),
                "processed_profiles": len(results),
                "input_file": config.input_file,
                "output_file": config.output_file,
                "max_profiles": config.max_profiles,
                "force_reextraction": config.force_reextraction
            }
        })
        
    except Exception as e:
        # Update job with error
        trait_extractor_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

async def run_airtable_updater_job(job_id: str, config: AirtableUpdaterConfig):
    """Background task to run Airtable update job."""
    try:
        # Update job status
        airtable_updater_jobs[job_id]["status"] = "running"
        
        # Update progress
        update_airtable_updater_job_progress(job_id, {
            "message": f"Starting Airtable update for {config.traits_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Initialize Airtable updater
        updater = AirtableTraitUpdater()
        
        # Update progress
        update_airtable_updater_job_progress(job_id, {
            "message": f"Loading trait data from {config.traits_file}",
            "timestamp": datetime.now().isoformat()
        })
        
        # Load data (we'll override the file paths)
        try:
            with open(config.traits_file, 'r', encoding='utf-8') as f:
                updater.trait_data = json.load(f)
            print(f"✓ Loaded {len(updater.trait_data)} trait extraction results")
            
            with open(config.url_mapping_file, 'r', encoding='utf-8') as f:
                updater.url_mapping = json.load(f)
            print(f"✓ Loaded {len(updater.url_mapping)} URL mappings")
            
        except FileNotFoundError as e:
            raise Exception(f"File not found: {e}")
        except Exception as e:
            raise Exception(f"Error loading data: {e}")
        
        update_airtable_updater_job_progress(job_id, {
            "message": f"Loaded {len(updater.trait_data)} traits and {len(updater.url_mapping)} mappings, starting updates",
            "total_traits": len(updater.trait_data),
            "total_mappings": len(updater.url_mapping),
            "processed_updates": 0,
            "timestamp": datetime.now().isoformat()
        })
        
        # Process trait extractions and update Airtable
        updater.process_trait_extractions(delay_between_updates=config.delay_between_updates)
        
        # Update job with results
        airtable_updater_jobs[job_id].update({
            "status": "completed",
            "completed_at": datetime.now(),
            "results": {
                "total_traits": len(updater.trait_data),
                "successful_updates": updater.update_results['successful_updates'],
                "failed_updates": updater.update_results['failed_updates'],
                "missing_mappings": updater.update_results['missing_mappings'],
                "traits_file": config.traits_file,
                "url_mapping_file": config.url_mapping_file
            }
        })
        
    except Exception as e:
        # Update job with error
        airtable_updater_jobs[job_id].update({
            "status": "failed",
            "completed_at": datetime.now(),
            "error": str(e)
        })

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Airtable LinkedIn URL Extractor API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "jobs": "/jobs",
            "extract": "/extract",
            "apify": "/apify/process",
            "cleaner": "/cleaner/process",
            "traits": "/traits/process",
            "airtable": "/airtable/update"
        }
    }

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint to check if the API is responsive."""
    return {
        "status": "ok",
        "message": "API is responsive",
        "timestamp": datetime.now().isoformat()
    }


'''
This actually calls the funciotn to extract all the linked in data

'''
@app.post("/extract", response_model=Dict[str, str])
async def start_extraction(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
):
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in extraction_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        extraction_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_extraction_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Extraction job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start extraction job: {str(e)}"
        )


@app.get("/status/{job_id}", response_model=ExtractionStatus)
async def get_job_status(job_id: str):
    """Get the status of an extraction job."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    job_data = extraction_jobs[job_id]
    return ExtractionStatus(**job_data)

@app.get("/results/{job_id}")
async def get_job_results(job_id: str):
    """Get the results of a completed extraction job."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    job_data = extraction_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/jobs")
async def list_jobs():
    """List all extraction jobs."""
    return {
        "total_jobs": len(extraction_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in extraction_jobs.items()
        ]
    }

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from memory."""
    if job_id not in extraction_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found"
        )
    
    del extraction_jobs[job_id]
    return {"message": f"Job '{job_id}' deleted successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in extraction_jobs.values() if j["status"] == "running"]),
        "total_jobs": len(extraction_jobs),
        "active_apify_jobs": len([j for j in apify_jobs.values() if j["status"] == "running"]),
        "total_apify_jobs": len(apify_jobs),
        "active_cleaner_jobs": len([j for j in data_cleaner_jobs.values() if j["status"] == "running"]),
        "total_cleaner_jobs": len(data_cleaner_jobs),
        "active_trait_jobs": len([j for j in trait_extractor_jobs.values() if j["status"] == "running"]),
        "total_trait_jobs": len(trait_extractor_jobs),
        "active_airtable_updater_jobs": len([j for j in airtable_updater_jobs.values() if j["status"] == "running"]),
        "total_airtable_updater_jobs": len(airtable_updater_jobs)
    }

@app.get("/terminal-logs")
async def get_terminal_logs():
    """Get terminal logs for display in frontend."""
    return {
        "logs": terminal_logs,
        "total_logs": len(terminal_logs),
        "max_logs": MAX_LOGS
    }

@app.delete("/terminal-logs")
async def clear_terminal_logs():
    """Clear all terminal logs."""
    global terminal_logs
    terminal_logs.clear()
    return {"message": "Terminal logs cleared successfully"}

# Apify Processing Endpoints
@app.post("/apify/process", response_model=Dict[str, str])
async def start_apify_processing(
    request: ApifyRequest,
    background_tasks: BackgroundTasks
):
    """Start a new Apify LinkedIn profile processing job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in apify_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        apify_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_apify_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Apify processing job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Apify processing job: {str(e)}"
        )

@app.get("/apify/status/{job_id}", response_model=ApifyStatus)
async def get_apify_job_status(job_id: str):
    """Get the status of an Apify processing job."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    job_data = apify_jobs[job_id]
    return ApifyStatus(**job_data)

@app.get("/apify/results/{job_id}")
async def get_apify_job_results(job_id: str):
    """Get the results of a completed Apify processing job."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    job_data = apify_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Apify job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/apify/jobs")
async def list_apify_jobs():
    """List all Apify processing jobs."""
    return {
        "total_jobs": len(apify_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in apify_jobs.items()
        ]
    }

@app.delete("/apify/jobs/{job_id}")
async def delete_apify_job(job_id: str):
    """Delete an Apify job from memory."""
    if job_id not in apify_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Apify job '{job_id}' not found"
        )
    
    del apify_jobs[job_id]
    return {"message": f"Apify job '{job_id}' deleted successfully"}

# Data Cleaner Endpoints
@app.post("/cleaner/process", response_model=Dict[str, str])
async def start_data_cleaning(
    request: DataCleanerRequest,
    background_tasks: BackgroundTasks
):
    """Start a new data cleaning job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in data_cleaner_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Data cleaner job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        data_cleaner_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_data_cleaner_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Data cleaning job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start data cleaning job: {str(e)}"
        )

@app.get("/cleaner/status/{job_id}", response_model=DataCleanerStatus)
async def get_data_cleaner_job_status(job_id: str):
    """Get the status of a data cleaning job."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    job_data = data_cleaner_jobs[job_id]
    return DataCleanerStatus(**job_data)

@app.get("/cleaner/results/{job_id}")
async def get_data_cleaner_job_results(job_id: str):
    """Get the results of a completed data cleaning job."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    job_data = data_cleaner_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data cleaner job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/cleaner/jobs")
async def list_data_cleaner_jobs():
    """List all data cleaning jobs."""
    return {
        "total_jobs": len(data_cleaner_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in data_cleaner_jobs.items()
        ]
    }

@app.delete("/cleaner/jobs/{job_id}")
async def delete_data_cleaner_job(job_id: str):
    """Delete a data cleaner job from memory."""
    if job_id not in data_cleaner_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data cleaner job '{job_id}' not found"
        )
    
    del data_cleaner_jobs[job_id]
    return {"message": f"Data cleaner job '{job_id}' deleted successfully"}

# Trait Extractor Endpoints
@app.post("/traits/process", response_model=Dict[str, str])
async def start_trait_extraction(
    request: TraitExtractorRequest,
    background_tasks: BackgroundTasks
):
    """Start a new trait extraction job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in trait_extractor_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Trait extractor job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        trait_extractor_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_trait_extractor_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Trait extraction job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start trait extraction job: {str(e)}"
        )

@app.get("/traits/status/{job_id}", response_model=TraitExtractorStatus)
async def get_trait_extractor_job_status(job_id: str):
    """Get the status of a trait extraction job."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    job_data = trait_extractor_jobs[job_id]
    return TraitExtractorStatus(**job_data)

@app.get("/traits/results/{job_id}")
async def get_trait_extractor_job_results(job_id: str):
    """Get the results of a completed trait extraction job."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    job_data = trait_extractor_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trait extractor job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/traits/jobs")
async def list_trait_extractor_jobs():
    """List all trait extraction jobs."""
    return {
        "total_jobs": len(trait_extractor_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in trait_extractor_jobs.items()
        ]
    }

@app.delete("/traits/jobs/{job_id}")
async def delete_trait_extractor_job(job_id: str):
    """Delete a trait extractor job from memory."""
    if job_id not in trait_extractor_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trait extractor job '{job_id}' not found"
        )
    
    del trait_extractor_jobs[job_id]
    return {"message": f"Trait extractor job '{job_id}' deleted successfully"}

# Airtable Updater Endpoints
@app.post("/airtable/update", response_model=Dict[str, str])
async def start_airtable_update(
    request: AirtableUpdaterRequest,
    background_tasks: BackgroundTasks
):
    """Start a new Airtable update job."""
    try:
        # Generate job ID if not provided
        job_id = request.job_id or generate_job_id()
        
        # Check if job already exists
        if job_id in airtable_updater_jobs:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Airtable updater job with ID '{job_id}' already exists"
            )
        
        # Initialize job
        airtable_updater_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "started_at": datetime.now(),
            "completed_at": None,
            "progress": {},
            "results": None,
            "error": None,
            "config": request.config.dict()
        }
        
        # Start background task
        background_tasks.add_task(run_airtable_updater_job, job_id, request.config)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Airtable update job started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Airtable update job: {str(e)}"
        )

@app.get("/airtable/status/{job_id}", response_model=AirtableUpdaterStatus)
async def get_airtable_updater_job_status(job_id: str):
    """Get the status of an Airtable update job."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    job_data = airtable_updater_jobs[job_id]
    return AirtableUpdaterStatus(**job_data)

@app.get("/airtable/results/{job_id}")
async def get_airtable_updater_job_results(job_id: str):
    """Get the results of a completed Airtable update job."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    job_data = airtable_updater_jobs[job_id]
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Airtable updater job '{job_id}' is not completed. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/airtable/jobs")
async def list_airtable_updater_jobs():
    """List all Airtable update jobs."""
    return {
        "total_jobs": len(airtable_updater_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job_data["status"],
                "started_at": job_data["started_at"],
                "completed_at": job_data.get("completed_at")
            }
            for job_id, job_data in airtable_updater_jobs.items()
        ]
    }

@app.delete("/airtable/jobs/{job_id}")
async def delete_airtable_updater_job(job_id: str):
    """Delete an Airtable updater job from memory."""
    if job_id not in airtable_updater_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Airtable updater job '{job_id}' not found"
        )
    
    del airtable_updater_jobs[job_id]
    return {"message": f"Airtable updater job '{job_id}' deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 