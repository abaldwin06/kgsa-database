# KGSA Alumni Tracking Python Program and Apps

This repository contains a program that manages automatic and manual imports into and exports from the KGSA Alumni Tracking Airtable database.

# To Use this Program
1. Download program to a folder
2. Create a Python v3.12.3 virtual environment and install `requirements.txt`
3. Request read/write access to the KGSA Airtable database from [Jedidah](mailto:jedidah@kgsafoundation.org) or [Anne](mailto:anne.baldwin06@gmail.com)
4. Log in and go to the [Airtable Create Token page](airtable.com/create/tokens) and create a token with read/write access to bases, tables/records, and comments.
5. Save your Access Token in a text file in the parent directory (one above where the `app.py` file is).
6. Update the app.py variable for the `access_key_filename`.

# Current Capabilities
1. Importing Zeraki data to create brand new student records in Airtable (using Zeraki ID, Name, and KCPE score)
2. Importing Zeraki data to update existing records in Airtable with new names or KCPE score (using Zeraki ID to match on the student)

# TODO 
- allow for importing zeraki data for students that don't have a zeraki ID in the system (matching just based on name)
- allow for selecting a type of grades and importing them