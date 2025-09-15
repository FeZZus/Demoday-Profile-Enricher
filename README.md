Theres a notion file in my workspace "Onstage Summer 25" 

# To run

- Activate the venv with `.\venv\Scripts\activate`
- then type in this: `.\emergency restart bat thing`
    - activates both front end and backend
- clicking each task once is enoguh - theres o output to show its running bar the terminal or the jobs page

https://airtable.com/appCicrQbZaRq1Tvo/api/docs#curl/table:startups —> get the base id and table id from here. These can be updated in the GlobalSettings.js file to set the default values to not have to re-enter them each time 

### 1. “Extract url’s” from airtable —> Airtable_extractor.py

- Give it the table id and the base id
- Then can just go through each stage and click go
- Setting the things at the top sets the prefixes for everything
- **Current issue:** Deleting the global prefix will cause it to reset itself which is stupid. but just delete part of it then type the part then delete the overhalf

### 2. “Process with apify” —> apify_requester.py

- Takes all the url’s, and runs them throguh apify
- this takes ages
- Costs £10 per 1000 results. so effectively 1p per person
- **Many of these can be run in parallel** - i think all can be run at same time without issues

### 3. Data cleaner:

- The apify linked in data is full of a lot of hyperlinks and bs
- So we clean it to just get the values of interest to us
- data_cleaner.py

### 4. Trait Extractor:

- Then the data is ran through gpt to extract traits from the data —> trait_extractor.py
- This is very slow
- Takes  a while but fairly cheap. took £5 to run like 15,000 profiles. Better models can be used ig in the future

### 5. “Airtable_field_creator.py” have to run manually:

- Have to run manually throguht the terminal
- Make sure venv is loaded first
- Also check that the base id and table id in main() is correct before running.
- Some of the values don’t work - the checkbox ones - so they have to be manually inserted into the airtable base

### 6. Update Airtable —> updates the base.

- It shoudl mostly just work
- Rate limited to 5 requests per second. Currently operating at 0.5 seconds delay per request. so tbh it coud be move to like 0.25 without much issue.
- airtable_updater.py