'''

# Step 1 airtable extractor - extracts all the linked in url's from the airtable. This has been done already. All 9k result profiles have been stored in the airtable extraction. 
# NOTE: Currently its checking purely for S25 results. missing/invalid url's are any such url's that are empty, or url's that have a different type of link in (i.e. to their website)

put data in airtable extractions so its not so messy
figure out if the 2 files are acc any diferent from each other - the 2 outputted json files. 
after this, it j needs to feed it into chatgpt and done.

ask issie what insights they actually want before i blow up all the credits and shit
THERES 1000 PROFILES, WITH APIFY THATS GONNA COST 100 QUID. 
'''

import os
from pyairtable import Api
from dotenv import load_dotenv
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

class AirtableLinkedInExtractor:
    """Extract LinkedIn URLs from Airtable for Apify processing."""
    
    def __init__(self):
        """Initialize the Airtable connection."""
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")
        
        self.api = Api(self.api_key)
        self.base_id = 'appCicrQbZaRq1Tvo'
        self.table_id = 'tblIJ47Fniuu9EJat' # original id is 'tblpzAcC0vMMibdca'
        self.table = self.api.table(self.base_id, self.table_id)
        
        # Data storage
        self.url_to_record_mapping: Dict[str, str] = {}
        self.valid_urls: List[str] = []
        self.invalid_urls: List[str] = []
        self.missing_urls: List[str] = {}  # record_id -> reason
        
    def is_valid_linkedin_url(self, url: str) -> bool:
        """Validate if the URL is a proper LinkedIn profile URL."""
        if not url or not isinstance(url, str):
            return False
        
        # Clean the URL
        url = url.strip()
        
        # Check for LinkedIn domain and profile pattern
        linkedin_pattern = r'https?://(?:www\.)?linkedin\.com/in/[\w\-]+/?(?:\?.*)?$'
        
        return bool(re.match(linkedin_pattern, url, re.IGNORECASE))
    
    def clean_linkedin_url(self, url: str) -> str:
        """Clean and standardize LinkedIn URL."""
        if not url:
            return url
            
        url = url.strip()
        
        # Remove query parameters and fragments
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # Ensure it ends with / for consistency
        if not clean_url.endswith('/'):
            clean_url += '/'
            
        return clean_url
    
    def extract_first_valid_linkedin_url(self, text: str) -> Optional[str]:
        """
        Extract the first valid LinkedIn URL from text that might contain multiple URLs.
        
        Args:
            text: Text that might contain one or more LinkedIn URLs
            
        Returns:
            First valid LinkedIn URL found, or None if none found
        """
        if not text or not isinstance(text, str):
            return None
        
        # Common separators for multiple URLs
        separators = [',', ';', ' ', '\n', '\t', '|']
        
        # Split by various separators
        potential_urls = [text.strip()]
        for separator in separators:
            temp_urls = []
            for url in potential_urls:
                temp_urls.extend([u.strip() for u in url.split(separator) if u.strip()])
            potential_urls = temp_urls
        
        # Filter to only LinkedIn-like URLs
        linkedin_candidates = [url for url in potential_urls if 'linkedin.com/in' in url.lower()]
        
        # If we found multiple potential LinkedIn URLs, log it
        if len(linkedin_candidates) > 1:
            print(f"    🔍 Multiple LinkedIn URLs found: {len(linkedin_candidates)} candidates")
            print(f"       Raw text: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Check each potential URL
        for i, url_candidate in enumerate(linkedin_candidates):
            cleaned_url = self.clean_linkedin_url(url_candidate)
            if self.is_valid_linkedin_url(cleaned_url):
                if len(linkedin_candidates) > 1:
                    print(f"       → Selected: {cleaned_url} (first valid)")
                return cleaned_url
        
        return None
    
    def extract_linkedin_urls(self, linkedin_fields: List[str] = None) -> Dict[str, any]:
        """
        Extract all LinkedIn URLs from Airtable.
        
        Args:
            linkedin_fields: List of field names to check for LinkedIn URLs
            
        Returns:
            Dictionary with extraction results and statistics
        """
        if linkedin_fields is None:
            linkedin_fields = [
                '4. CEO LinkedIn'
            ]
        
        print("Starting LinkedIn URL extraction from Airtable...")
        print(f"Base ID: {self.base_id}")
        print(f"Table ID: {self.table_id}")
        print(f"Checking fields: {linkedin_fields}")
        print("-" * 60)
        
        total_records = 0
        processed_pages = 0
        
        try:
            # Iterate through all records in the table
            for records in self.table.iterate(page_size=100):
                processed_pages += 1
                print(f"Processing page {processed_pages} ({len(records)} records)...")
                
                for record in records:
                    total_records += 1
                    #print(record)
                    record_id = record['id']
                    fields = record.get('fields', {})
                    
                    
                    linkedin_url = None
                    found_field = None
             

                    filter_condition = {'Event': 'S25', 'Top 100': True}
                    flag = True
                    for filter in filter_condition:
                        if filter not in fields or fields[filter] != filter_condition[filter]:
                            flag = False
                    if flag:
                        # Check each potential LinkedIn field (theres only one that matters atm)
                        for field_name in linkedin_fields:
                            if field_name in fields and fields[field_name]:
                                url_candidate = fields[field_name]
                                
                                # Handle case where field might be a list
                                if isinstance(url_candidate, list):
                                    url_candidate = url_candidate[0] if url_candidate else None
                                
                                if isinstance(url_candidate, str) and 'linkedin.com/in' in url_candidate.lower():
                                    # Use new method to extract first valid LinkedIn URL
                                    linkedin_url = self.extract_first_valid_linkedin_url(url_candidate)
                                    if linkedin_url:
                                        found_field = field_name
                                        break
                        # record_id = ""
                        # if '6. Company name' in fields:
                        #     record_id = fields['6. Company name']
                        # print(record_id)
                    
                        # Process the found URL
                        if linkedin_url:
                            # URL is already cleaned and validated by extract_first_valid_linkedin_url
                            # Avoid duplicates
                            if linkedin_url not in self.url_to_record_mapping:
                                self.url_to_record_mapping[linkedin_url] = record_id
                                self.valid_urls.append(linkedin_url)
                                print(f"  ✓ Valid: {linkedin_url}")
                            else:
                                print(f"  ~ Duplicate: {linkedin_url}")
                        else:
                            # Track records without LinkedIn URLs
                            self.missing_urls[record_id] = "No valid LinkedIn URL found in any field"
                            if total_records <= 100:  # Only show first few missing ones
                                print(f"  - No LinkedIn URL found for record {record_id}")
            
            # Print summary
            self.print_summary(total_records)
            
            # Save results
            self.save_results()
            
            return {
                'total_records': total_records,
                'valid_urls': len(self.valid_urls),
                'invalid_urls': len(self.invalid_urls),
                'missing_urls': len(self.missing_urls),
                'url_to_record_mapping': self.url_to_record_mapping,
                'urls_for_apify': self.valid_urls
            }
            
        except Exception as e:
            print(f"Error during extraction: {e}")
            raise
    
    def print_summary(self, total_records: int):
        """Print extraction summary."""
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Total records processed: {total_records}")
        print(f"Valid LinkedIn URLs found: {len(self.valid_urls)}")
        print(f"Invalid URLs found: {len(self.invalid_urls)}")
        print(f"Records without LinkedIn URLs: {len(self.missing_urls)}")
        print(f"Success rate: {len(self.valid_urls)/total_records*100:.1f}%")
        
        if self.invalid_urls:
            print(f"\nFirst few invalid URLs:")
            for url in self.invalid_urls[:5]:
                print(f"  - {url}")
            if len(self.invalid_urls) > 5:
                print(f"  ... and {len(self.invalid_urls) - 5} more")
    
    def save_results(self):
        """Save extraction results to JSON files."""
        # Save URL to record mapping (for updating Airtable later)
        with open('airtable-extractions\\S25Top100airtable_url_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(self.url_to_record_mapping, f, indent=2, ensure_ascii=False)
        
        # Save URLs for Apify (clean list)
        with open('airtable-extractions\\S25Top100linkedin_urls_for_apify.json', 'w', encoding='utf-8') as f:
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
        
        with open('airtable-extractions\\S25Top100airtable_extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Files saved:")
        print(f"  - airtable_url_mapping.json (URL → Record ID mapping)")
        print(f"  - linkedin_urls_for_apify.json (Clean URLs for Apify)")
        print(f"  - airtable_extraction_results.json (Complete results)")

def main():
    """Main execution function."""
    try:
        extractor = AirtableLinkedInExtractor()
        results = extractor.extract_linkedin_urls()
        
        print(f"\n✅ Extraction complete!")
        print(f"Ready for Apify: {len(results['urls_for_apify'])} LinkedIn URLs")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()