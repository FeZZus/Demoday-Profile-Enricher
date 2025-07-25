'''
step 2: after extracting linkedins through airtable, we use apify to get all the data from the users profiles
Note: this is currenlty only requesting s25 profiles. Currently it's doing 900 profiles only in the test mode
To get off test mode, change the test flag.

THIS NEEDS TO ALSO ADD THE RECORD ID WHICH SHOULD GO THROUGH EVERY OTHER STAGE TO GET TO THE OUTPUT AT THE END. NO POINT MATCHING LINKED IN URL'S AND STUFF

'''


import json
from apify_client import ApifyClient
import time
import os
import dotenv

dotenv.load_dotenv()

def load_linkedin_urls(file_path):
    """Load LinkedIn URLs from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            urls = json.load(file)
        print(f"Loaded {len(urls)} URLs from {file_path}")
        return urls
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}")
        return []

def save_results_to_json(results, output_file):
    """Save results to JSON file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")
    except Exception as e:
        print(f"Error saving results: {e}")

def load_existing_results(output_file):
    """Load existing results from file if it exists"""
    try:
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as file:
                results = json.load(file)
            print(f"Loaded {len(results)} existing results from {output_file}")
            return results
    except Exception as e:
        print(f"Error loading existing results: {e}")
    return []

def load_progress(progress_file):
    """Load progress tracking file"""
    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as file:
                progress = json.load(file)
            return progress.get('processed_urls', [])
    except Exception as e:
        print(f"Error loading progress: {e}")
    return []

def save_progress(progress_file, processed_urls):
    """Save progress tracking file"""
    try:
        os.makedirs(os.path.dirname(progress_file), exist_ok=True)
        progress_data = {
            'processed_urls': processed_urls,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(progress_file, 'w', encoding='utf-8') as file:
            json.dump(progress_data, file, indent=2)
    except Exception as e:
        print(f"Error saving progress: {e}")

def append_results_to_file(new_results, output_file):
    """Append new results to existing file"""
    try:
        existing_results = load_existing_results(output_file)
        existing_results.extend(new_results)
        save_results_to_json(existing_results, output_file)
        return len(existing_results)
    except Exception as e:
        print(f"Error appending results: {e}")
        return 0

def get_remaining_urls(all_urls, processed_urls):
    """Get URLs that haven't been processed yet"""
    processed_set = set(processed_urls)
    remaining = [url for url in all_urls if url not in processed_set]
    return remaining

def process_linkedin_profiles_with_resume(api_token, urls, output_file="apify-profile-data\\linkedin_profile_data.json", batch_size=50):
    """Process LinkedIn URLs through Apify with progressive saving and resume capability"""
    
    # Set up progress tracking
    progress_file = output_file.replace('.json', '_progress.json')
    
    # Load existing progress
    processed_urls = load_progress(progress_file)
    remaining_urls = get_remaining_urls(urls, processed_urls)
    
    if not remaining_urls:
        print("✅ All URLs have already been processed!")
        existing_results = load_existing_results(output_file)
        return existing_results
    
    print(f"📊 Progress Status:")
    print(f"  Total URLs: {len(urls)}")
    print(f"  Already processed: {len(processed_urls)}")
    print(f"  Remaining to process: {len(remaining_urls)}")
    
    if len(processed_urls) > 0:
        print(f"🔄 RESUMING from {len(processed_urls)} completed profiles")
    
    # Initialize the ApifyClient
    client = ApifyClient(api_token)
    
    # Process URLs in batches
    all_new_results = []
    total_processed = len(processed_urls)
    
    for i in range(0, len(remaining_urls), batch_size):
        batch_urls = remaining_urls[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(remaining_urls) + batch_size - 1) // batch_size
        
        print(f"\n🔄 Processing batch {batch_num}/{total_batches} ({len(batch_urls)} URLs)")
        
        # Prepare the Actor input for this batch
        run_input = {
            "profileUrls": batch_urls
        }
        
        try:
            # Run the Actor for this batch
            print(f"  Starting Apify actor for batch {batch_num}...")
            run = client.actor("2SyF0bVxmgGr8IVCZ").call(run_input=run_input)
            
            print(f"  Actor completed for batch {batch_num}. Fetching results...")
            
            # Fetch results for this batch
            batch_results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                batch_results.append(item)
                total_processed += 1
                print(f"    Processed ({total_processed}/{len(urls)}): {item.get('name', 'Unknown')}")
            
            # Save this batch immediately
            if batch_results:
                all_new_results.extend(batch_results)
                total_saved = append_results_to_file(batch_results, output_file)
                
                # Update progress tracking
                batch_processed_urls = [item.get('url', batch_urls[idx]) for idx, item in enumerate(batch_results)]
                processed_urls.extend(batch_processed_urls)
                save_progress(progress_file, processed_urls)
                
                print(f"  ✅ Batch {batch_num} saved! Total profiles in file: {total_saved}")
            else:
                print(f"  ⚠️ No results obtained for batch {batch_num}")
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < len(remaining_urls):
                print(f"  ⏳ Waiting 5 seconds before next batch...")
                time.sleep(5)
                
        except Exception as e:
            print(f"  ❌ Error processing batch {batch_num}: {e}")
            print(f"  💾 Progress saved up to batch {batch_num - 1}")
            break
    
    print(f"\n🎉 Processing completed!")
    print(f"📊 Final Statistics:")
    print(f"  Total URLs: {len(urls)}")
    print(f"  Successfully processed: {total_processed}")
    print(f"  New profiles in this session: {len(all_new_results)}")
    
    # Load and return all results
    final_results = load_existing_results(output_file)
    return final_results

def process_linkedin_profiles(api_token, urls, output_file="apify-profile-data\\linkedin_profile_data.json"):
    """Original process function - now redirects to the resume-enabled version"""
    return process_linkedin_profiles_with_resume(api_token, urls, output_file)

def test_apify_script(api_token, urls_file, num_urls=3):
    """Test the Apify script with a limited number of URLs"""
    
    print(f"\n🧪 TESTING MODE: Processing only {num_urls} URLs")
    print("=" * 50)
    
    # Load all URLs
    all_urls = load_linkedin_urls(urls_file)
    
    if not all_urls:
        print("No URLs loaded for testing")
        return []
    
    # Take only the specified number of URLs for testing
    test_urls = all_urls[:num_urls]
    
    print(f"Selected {len(test_urls)} URLs for testing:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    # Process the test URLs
    test_output_file = f"apify-profile-data\\test_linkedin_profiles_{num_urls}_urls.json"
    results = process_linkedin_profiles_with_resume(api_token, test_urls, test_output_file, batch_size=2)
    
    if results:
        print(f"\n✅ TEST COMPLETED SUCCESSFULLY!")
        print(f"✅ Processed {len(results)} out of {len(test_urls)} test URLs")
        print(f"✅ Test results saved to {test_output_file}")
        
        # Display sample result
        if results:
            print(f"\n📋 Sample result preview:")
            sample = results[0]
            print(f"  Name: {sample.get('name', 'N/A')}")
            print(f"  Title: {sample.get('title', 'N/A')}")
            print(f"  Location: {sample.get('location', 'N/A')}")
            print(f"  Company: {sample.get('company', 'N/A')}")
    else:
        print(f"\n❌ TEST FAILED - No results obtained")
    
    return results

if __name__ == "__main__":
    # Configuration
    API_TOKEN = os.getenv('APIFY_API_KEY')  # Replace with your actual Apify API token
    URLS_FILE = "airtable-extractions\\S25Top100linkedin_urls_for_apify.json"
    OUTPUT_FILE = "apify-profile-data\\S25Top100linkedin_profile_data.json"
    BATCH_SIZE = 50  # Process URLs in batches of 50
    
    # Choose mode: Test or Full processing
    TEST_MODE = False  # Set to False for full processing
    TEST_NUM_URLS = 900  # Number of URLs to test with
    
    if TEST_MODE:
        # Test mode - process only a few URLs
        test_results = test_apify_script(API_TOKEN, URLS_FILE, TEST_NUM_URLS)
    else:
        # Full processing mode
        print("\n🚀 FULL PROCESSING MODE")
        print("=" * 50)
        
        # Load URLs from file
        linkedin_urls = load_linkedin_urls(URLS_FILE)
        
        if linkedin_urls:
            # Process URLs through Apify with resume capability
            results = process_linkedin_profiles_with_resume(API_TOKEN, linkedin_urls, OUTPUT_FILE, BATCH_SIZE)
            
            if results:
                print(f"\n✓ Successfully processed {len(results)} LinkedIn profiles")
                print(f"✓ Results saved to {OUTPUT_FILE}")
            else:
                print("\n✗ No results obtained from Apify")
        else:
            print("No URLs to process")