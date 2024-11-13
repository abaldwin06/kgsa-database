# KGSA Alumni Tracking Python Program and Apps

This repository contains a program that manages automatic and manual imports into and exports from the KGSA Alumni Tracking Airtable database.

# To Set Up this Program
1. Download program to a folder
2. Create a Python v3.12.3 virtual environment and install `requirements.txt`
3. Request read/write access to the KGSA Airtable database from [Jedidah](mailto:jedidah@kgsafoundation.org) or [Anne](mailto:anne.baldwin06@gmail.com)
4. Log in and go to the [Airtable Create Token page](airtable.com/create/tokens) and create a token with read/write access to bases, tables/records, and comments.
5. Save your Access Token in a text file in the parent directory (one above where the `app.py` file is).
6. Update the app.py variable for the `access_key_filename`.

# Current Capabilities
## Import data from Zeraki
Import can create new student records, match to existing records using zeraki ID or name, update records with zeraki numbers, different names, KCPE scores etc. 
1. Copy grades table into a csv file and move file into `to-import` folder. Naming convention for files: `Zeraki Files - [C#### FOR GRAD CLASS] [EXAM TYPE] - [GRADE YEAR]`
2. Open a terminal window, navigate to the project folder and activate python environment `source .env/bin/activate`
3. Run import script:
 * In test mode:`python3 app.py` (no edits committed to DB) 
 * In import/edit mode: `python3 app.py -f import` (edits committed to DB)
4. At the selection prompt you will have options to either
 * Import Students and KCPE scores
 * Import Grades (not yet supported)
5. The next selection prompt will allow you to select a file from the `to-import` folder

### Import Students, Zeraki ID, KCPE Scores
1. The program will go row by row and
 * Match the Zeraki csv data to a Student in the Airtable database, allowing the user to confirm matches that aren't matched by Zeraki ID or Full Name
 * Compare the data in the Zeraki csv to the data in the Airtable database for the matched Student
 * The user is able to select field by field if new data should be added to the Airtable record, or updated if the values differ between databases

### Import Term Grades from Zeraki
Coming soon

## Export Data from Airtable to JSON files
1. Open a terminal window, navigate to the project folder and activate python environment `source .env/bin/activate`
2. Run this the export: `python3 export.py`
3. Data will file to JSON files in `.export/` subdirectory.

# TODO 
[x] update zeraki headers check to go by header name
[x] match based on name
[x] have a test mode (where edits aren't made to the db)
[x] able to update item by item (do you want to update zeraki num? kcpe? name?)
[x] fix check for field errors function
[x] fix how it says it was unsuccessful at updating but it actually was (and this messes up the count)
[x] have a setting for always considering full name matches a match (no user input) - this is default now
[x] import zeraki nums for 2023, 2022, 2021?
---
[ ] allow for selecting a type of grade and date of grades (term one, term two)
[ ] able to identify the subject based on the header
[ ] parse the numeric and letter grade from the csv
[ ] able to create a new test scores row for each grade and link it to the right student