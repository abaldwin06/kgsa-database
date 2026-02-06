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
## Prerequisite to Download CSVs from Zeraki
1. You need to be set up as a Zeraki user with super admin priviliges. 
2. You then navigate to a set of test scores, click "download" and select "merit list" and download as spreadsheet.

## Import data from Zeraki
Import can create new student records, match to existing records using zeraki ID or name, update records with zeraki numbers, different names, KCPE scores, KCSE scores, term grades etc. 
1. Download a spreadsheet (.xlsx) file from Zeraki and save to the `to_import` folder
2. Open a terminal window, navigate to the project folder and activate python environment `source .env/bin/activate`
3. Run import script:
 * In test mode:`python3 app.py` (no edits committed to DB) 
 * In import/edit mode: `python3 app.py -f import` (edits committed to DB)
4. At the selection prompt you will have options to either
 * Import Students and KCPE scores
 * Import Grades (not yet supported)
5. The next selection prompt will allow you to select a file from the `to-import` folder
6. If the file is an .xlsx file and you select it, you will be prompted for details about the scores in that file. This will take the active sheet of the spreadsheet and convert it to a .csv file using the naming convention: `[C#### FOR GRAD CLASS] - [EXAM TYPE] - F# - [TEST DATE].csv`

### Import Students, Zeraki ID, KCPE Scores
1. Once a file is selected, the program will have you select which grad class the data is for.
2. Next the program will go row by row and:
 * Match the Zeraki csv data to a Student in the Airtable database, allowing the user to confirm matches that aren't matched by Zeraki ID or Full Name
 * Compare the data in the Zeraki csv to the data in the Airtable database for the matched Student
 * The user is able to select field by field if new data should be added to the Airtable record, or updated if the values differ between databases. Fields to update include: Zeraki ID, Name, KCPE scores.

### Import Term Grades or KCSE scores from Zeraki
1. Once a file is selected, the program will have you select the following (if not already embedded in the CSV name):
 * Which grad class the data is for
 * What type of test scores are to be imported (Term 1, 2, 3, mid term, end term, KCSE etc)
 * The date the test scores were generated
2. Next the program will go row by row and:
 * Match the Zeraki csv data to a Student in the Airtable database, allowing the user to confirm matches that aren't matched by Zeraki ID or Full Name
 * Create a series of test score records linked to that student, that have the specified test score date and type

## Export Data from Airtable to JSON files
1. Open a terminal window, navigate to the project folder and activate python environment `source .env/bin/activate`
2. Run this the export: `python3 export.py`
3. Data will file to JSON files in `.export/` subdirectory.

# TODO 
- [ ] delete or move XLSX files or already imported grades
- [ ] add a way to deal with duplicate zeraki numbers  (2027 - emmaculate)
- [ ] checking for duplicate grates doesn't work 
- [ ] combine importing students and grades
- [ ] Add a function to store Zeraki name to DB so we stop asking for name matches OR add a way to opt out of name changes in both import types
- [ ] fix bug with matching by last name:
    >    File "/Users/annebaldwin/Documents/projects/kgsa-database/app.py", line 374, in find_match_by_name
    >         db_last_name = student['fields']['Last name'].upper()
    >    To recreate, remove the zeraki num from AT for a student that matches by last name (Anne Achieng Juma 2024) and try to import students

Things completed:
- [X] imported all grades to date
- [X] test updating the student list
- [X] test any issues with the convert integer and string values function (convert_numeric_values function)
- [X] resolve issue where there is an error of TT PTS not being a number
- [X] create function to change .xlsx to csv and delete top row
- [X] update import to parse out test type etc from file name
- [X] add a function to ImportRecord to return an array of grade records in Airtable format, update record_dict function to work for students and grades
- [X] able to create a new test scores row for each grade and link it to the right student
- [X] create optional duplicate checking function
- [X] fix "add_grade" function to work for both numeric/string scores
- [X] add function to ImportRecord to print out any grades stored and ready to import and test
- [X] pass in test type, date, form etc into importrecord init function for storage of grades to import
- [X] update import_grades to match on a student by znum or full name (no kcpe or name changes)
- [X] update import_grades to do a printout of the above
- [x] update zeraki headers check to go by header name
- [x] match based on name
- [x] have a test mode (where edits aren't made to the db)
- [x] able to update item by item (do you want to update zeraki num? kcpe? name?)
- [x] fix check for field errors function
- [x] fix how it says it was unsuccessful at updating but it actually was (and this messes up the count)
- [x] have a setting for always considering full name matches a match (no user input) - this is default now
- [x] import zeraki nums for 2023, 2022, 2021?
- [x] allow for selecting a type of grade and date of grades (term one, term two)