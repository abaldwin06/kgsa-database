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
## Zeraki Imports
Steps to import data from Zeraki:
1. Copy grades table into a csv file and move file into `to-import` folder. Naming convention for files: `Zeraki Files - [C#### FOR GRAD CLASS] [EXAM TYPE] - [GRADE YEAR]`
2. Open a terminal window, navigate to the project folder and activate python environment `source .env/bin/activate`
3. Run import script `python3 app.py`
4. At the selection prompt you will have options to import term grades or Students and KCPEs. Select your preference.
5. The next selection prompt will allow you to select a file from the `to-import` folder


1. Importing Zeraki data to create brand new student records in Airtable (using Zeraki ID, Name, and KCPE score)
2. Importing Zeraki data to update existing records in Airtable with new names or KCPE score (using Zeraki ID to match on the student)

# TODO 
[x] update zeraki headers check to go by header name
[x] match based on name
[x] have a test mode (where edits aren't made to the db)
[x] able to update item by item (do you want to update zeraki num? kcpe? name?)
[ ] fix check for field errors function
[ ] fix how it says it was unsuccessful at updating but it actually was (and this messes up the count)
[ ] have a setting for always considering full name matches a match (no user input)
[ ] import zeraki nums for 2022, 2022, 2021?
---
[ ] allow for selecting a type of grade and date of grades (term one, term two)
[ ] able to identify the subject based on the header
[ ] parse the numeric and letter grade from the csv
[ ] able to create a new test scores row for each grade and link it to the right student