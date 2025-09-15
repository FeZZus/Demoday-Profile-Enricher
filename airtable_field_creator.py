'''
Step 5 or 6, creat the required airtable fields

Script to automatically create missing AI fields in Airtable.
This will create all the necessary fields with appropriate data types.
'''

import os
import time
import requests
from pyairtable import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AirtableFieldCreator:
    """Create missing AI fields in Airtable."""
    
    def __init__(self, base_id: str, table_id: str):
        """Initialize the Airtable connection."""
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        if not self.api_key:
            raise ValueError("AIRTABLE_API_KEY environment variable not set")
        
        self.api = Api(self.api_key)
        self.base_id = base_id
        self.table_id = table_id
        self.table = self.api.table(self.base_id, self.table_id)
    
    def get_field_definitions(self):
        """Define all AI fields with their appropriate data types."""
        
        field_definitions = [
            # Basic info fields
            {'name': 'AI_Full_Name', 'type': 'singleLineText'},
            {'name': 'AI_Estimated_Age', 'type': 'singleLineText'},  
            {'name': 'AI_Confidence_Score', 'type': 'singleSelect', 'options': {
                'choices': [
                    {'name': 'High', 'color': 'greenBright'},
                    {'name': 'Medium', 'color': 'yellowBright'},
                    {'name': 'Low', 'color': 'redBright'}
                ]
            }},
            
            # Education fields
            {'name': 'AI_Undergraduate', 'type': 'multilineText'},
            {'name': 'AI_Masters', 'type': 'multilineText'},
            {'name': 'AI_PhD', 'type': 'multilineText'},
            {'name': 'AI_Other_Education', 'type': 'multilineText'},
            
            # Career insights (numbers)
            {'name': 'AI_Avg_Tenure_Per_Role', 'type': 'number', 'options': {'precision': 2}},
            {'name': 'AI_Total_Experience_Count', 'type': 'number', 'options': {'precision': 0}},
            {'name': 'AI_Founder_Experience_Count', 'type': 'number', 'options': {'precision': 0}},
            {'name': 'AI_Industry_Switches', 'type': 'number', 'options': {'precision': 0}},
            {'name': 'AI_Total_Years_Experience', 'type': 'number', 'options': {'precision': 2}},
            {'name': 'AI_Years_Out_Of_Education', 'type': 'number', 'options': {'precision': 0}},
            {'name': 'AI_Years_In_Industry', 'type': 'number', 'options': {'precision': 0}},
            
            # Career insights (checkboxes/booleans)
            {'name': 'AI_Job_Hopper', 'type': 'checkbox'},
            {'name': 'AI_Has_Leadership_Experience', 'type': 'checkbox'},
            {'name': 'AI_Has_C_Suite_Experience', 'type': 'checkbox'},
            
            # Career summary (long text)
            {'name': 'AI_Career_Summary', 'type': 'multilineText'},
            
            # Company background
            {'name': 'AI_Notable_Companies', 'type': 'multilineText'},
            {'name': 'AI_Startup_Companies', 'type': 'multilineText'},
            
            # Accelerators and programs
            {'name': 'AI_Accelerators', 'type': 'multilineText'},
            {'name': 'AI_Fellowship_Programs', 'type': 'multilineText'},
            {'name': 'AI_Board_Positions', 'type': 'multilineText'},
            
            # Education-career alignment
            {'name': 'AI_Studies_Field', 'type': 'singleLineText'},
            {'name': 'AI_Current_Field', 'type': 'singleLineText'},
            {'name': 'AI_Pivot_Description', 'type': 'multilineText'},
            
            # Personal brand
            {'name': 'AI_Headline_Keywords', 'type': 'multilineText'},
            
            # Academic and research
            {'name': 'AI_Academic_Roles', 'type': 'multilineText'},
            
            # International experience
            {'name': 'AI_Countries_Worked', 'type': 'multilineText'},
            {'name': 'AI_Global_Companies', "type": "checkbox"},
        ]
        
        return field_definitions
    
 
    def create_field(self, field_def):
        """Create a single field in Airtable."""
        try:
            # Use the Meta API to create fields
            # Note: This requires special permissions and might not work with all API keys
            base_url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables/{self.table_id}/fields"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(base_url, json=field_def, headers=headers)
            
            
            if response.status_code == 200:
                return True
            else:
                print(f"  ❌ Failed to create {field_def['name']}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error creating field {field_def['name']}: {e}")
            return False
    
    def create_missing_fields(self):
        """Create all missing AI fields."""
        print("🚀 Creating missing AI fields in Airtable...")
        print("-" * 60)
        
        # Get field definitions
        field_definitions = self.get_field_definitions()
        
        # Check existing fields
        
        # Filter to only missing fields
        missing_fields = [f for f in field_definitions]
        
        if not missing_fields:
            print("✅ All AI fields already exist!")
            return True
        
        print(f"📝 Creating {len(missing_fields)} missing fields...")
        
        created_count = 0
        failed_count = 0
        
        for i, field_def in enumerate(missing_fields):
            print(f"Creating {i+1}/{len(missing_fields)}: {field_def['name']}")
            
            if self.create_field(field_def):
                print(f"  ✅ Created successfully")
                created_count += 1
            else:
                failed_count += 1
            
            # Rate limiting - Airtable API has limits
            time.sleep(0.5)
        
        print(f"\n📊 SUMMARY:")
        print(f"✅ Successfully created: {created_count} fields")
        print(f"❌ Failed to create: {failed_count} fields")
        
        if created_count > 0:
            print(f"\n🎉 Ready to run airtable_updater.py!")
        
        return failed_count == 0

def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create missing AI fields in Airtable')
    parser.add_argument('--base-id', default='appCicrQbZaRq1Tvo', help='Airtable base ID')
    parser.add_argument('--table-id', default='tblpzAcC0vMMibdca', help='Airtable table ID')
    
    args = parser.parse_args()
    
    try:
        creator = AirtableFieldCreator(args.base_id, args.table_id)
        success = creator.create_missing_fields()
        
        if success:
            print("\n✅ All fields created successfully!")
        else:
            print("\n⚠️  Some fields failed to create. You may need to create them manually in Airtable.")
            print("\nMANUAL CREATION GUIDE:")
            print("1. Go to your Airtable base")
            print("2. Click '+' to add new fields")
            print("3. Use the field names and types shown above")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Alternative: Create fields manually in Airtable:")
        print("   - Go to your Airtable table")
        print("   - Click the '+' button to add fields") 
        print("   - Create fields with names like: AI_Full_Name, AI_Estimated_Age, etc.")
        return False
    
    return True

if __name__ == "__main__":
    main() 