import os
import csv
from typing import List, Tuple, Optional, TextIO, Literal
from pyairtable import Api, formulas, Table, Base
from pyairtable.api.types import RecordDict
from pyairtable.models.schema import FieldSchema
import argparse
import json

class DuplicateRecordError(Exception):
    pass

class ImportRecord:
    # properties:
    # csv_row, zeraki_num, zeraki_name, kcpe, first_name, last_name, at_id, match_type, matched_record, at_edit type
    def __init__(self,row:List,headers:List,csv_row_num:int) -> bool:
        self.csv_row = csv_row_num
        for idx,header in enumerate(headers):
            if header == 'ADMNO':
                self.zeraki_num = row[idx]
            elif header == 'NAME':
                self.zeraki_name = row[idx].upper()
                self.parse_names()
            elif header == 'KCPE':
                try:
                    self.kcpe = int(row[idx])
                except ValueError:
                    pass

    def get(self,prop_name:str):
        val = getattr(self, prop_name, None)
        return val if val != "" else None

    def name(self,name_type='full'):
        first_name = self.get('first_name')
        last_name = self.get('last_name')
        zeraki_name = self.get('zeraki_name')
        if name_type == 'full':
            if first_name and last_name:
                return f"{first_name.strip()} {last_name.strip()}"
            elif zeraki_name:
                return zeraki_name.strip()
            else:
                return "No name"
        elif name_type == 'first':
            if first_name:
                return first_name.strip()
            else:
                return 'No first name'
        elif name_type == 'last':
            if last_name:
                return last_name.strip()
            else:
                return 'No last name'
        else:
            return self.name('full')

    def __repr__(self) -> str:
        text=''
        try:
            text = text + f"""
            Zeraki ADM No: """ + self.get('zeraki_num')
        except TypeError:
            pass
        try:
            text = text + f"""
            Matched by """+self.get('match_type')+" to Airtable ID: " + self.get('at_id')
        except TypeError:
            pass
        try:
            text = text + f"""
            Student: """ + self.name()
        except TypeError:
            #shouldn't happen
            pass
        try:
            text = text + f"""
            KCPE score: """+ str(self.get('kcpe'))
        except TypeError:
            pass
        return text

    def parse_names(self):
        try:
            names = self.get('zeraki_name').split(' ')
        except TypeError:
            print(f"Row {self.get('csv_row')}: Error splitting Student Name, no Zeraki Name present, skipping student.")
            return
        name_count = len(names)
        if name_count < 2:
            print(f"Row {self.get('csv_row')}: Error splitting Student Name, unexpected number of names: {self.get('zeraki_name')}.")
        else:
            self.first_name = names[0]
            self.last_name = " ".join(names[1:])
            #print(f"Row {self.csv_row}: First name: {self.first_name}, Last name: {self.last_name}.")

    def return_import_dict(self,at_id=None):
        import_dict = {}
        if self.get('at_id'):
            import_dict['ID'] = self.get('at_id')
        import_dict['Zeraki ADM No'] = self.get('zeraki_num')
        import_dict['First name'] = self.name('first').title()
        import_dict['Last name'] = self.name('last').title()
        if self.get('grad_year'):
            import_dict['Grad Class'] = self.get('grad_year')
        if self.get('kcpe'):
            import_dict['KCPE Score'] = self.get('kcpe')
        return import_dict

# User Input Functions
def user_selection(options_list:List[str],quit_allowed:bool=True) -> str:
    for idx, option in enumerate(options_list,start=1):
        print(f"{idx}: {option}")
    
    # Get user input
    while True:
        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice in ['q','quit'] and quit_allowed == True:
            print("Quitting the program.")
            return 'quit'
        else:
            try:
                user_choice_int = int(user_choice)
                if user_choice_int <= 0 or user_choice_int > len(options_list):
                    print("Invalid number entered. Please enter a valid number.")
                else:
                    selected_option = options_list[user_choice_int-1]
                    print(f"You have selected: {selected_option}")
                    print("")
                    return selected_option
            except ValueError as e:
                print("Please enter a valid number.")   

def list_files(directory:str) -> List[str]:
    """List all files in the given directory and return a list of file names.

    Args:
        directory (str): pull path to the 'to-import' folder, expected in the parent directory of th eprogram

    Returns:
        List[str]: list of filepaths to files in the 'to-import' folder
    """
    files = os.listdir(directory)
    files = [f for f in files if os.path.isfile(os.path.join(directory, f))]
    return files

def select_file() -> Optional[TextIO]:
    """Select the CSV file to import into Airtable from the files in the 'to-import' 
       folder within the current directory

    Returns:
        string: file contents of user selected file, or 'quit' if user wants to exit program
    """
    
    folder_name = './to-import'
    
    # Check if the directory exists
    if not os.path.isdir(folder_name):
        print(f"The directory '{folder_name}' does not exist.")
        return
    
    # List files in the directory
    files = list_files(folder_name)
    
    if not files:
        print(f"No files found in the directory '{folder_name}'.")
        return

    # Display the files with an index number
    print("Please choose a file to import:")
    selected_file_name = user_selection(files)
    if selected_file_name == 'quit':
            return None
    else:
        # Full path of the selected file
        selected_file_path = os.path.join(folder_name, selected_file_name)
        selected_file = open(selected_file_path,mode="r",newline='')
        return selected_file

def print_dict(d:dict):
    print(json.dumps(d, indent=4))

def compare_students(csv_data:dict,db_data:dict):
    keys_to_update = []
    print("Proposed updates to the DB:")

    for key,csv_val in csv_data.items():

        # DATA TO BE ADDED
        if key not in db_data.keys():
            print(f" -add-  {key}: {csv_val}")
            keys_to_update.append(key)
        else:
            db_val = db_data[key]
            #check for matching data
            if csv_val == db_val:
                equal = True
            #make matching values case insensitive for strings
            elif isinstance(csv_val,str) and isinstance(db_val,str):
                if csv_val.upper() == db_val.upper():
                    equal = True
                else:
                    equal = False
            else:
                #check for values that are string in one system and int in another  
                try:
                    if str(csv_val) == str(db_val):
                        equal = True
                    else:
                        equal = False
                except TypeError:
                    equal = False

            # DATA THAT WON'T BE CHANGED
            if equal:
                print(f"        {key}: {db_val}")

            # DATA TO BE UPDATED
            else:    
                print(f" -edit- {key}: {db_data[key]} -> {csv_val}")
                keys_to_update.append(key)
    
    print("")
    return keys_to_update

# CSV Processing Functions
def parse_csv(file:TextIO) -> Optional[List[List[str]]]:
    reader = csv.reader(file)
    headers = next(reader)  # Assume first row is headers
    # create a 2D list of CSV data
    #   each list item is a row of data, 
    #       each row of data is represented as a list of col values
    data = [row for row in reader]
    return data,headers

def csv_to_import_records(file:TextIO):
    data,headers = parse_csv(file)
    import_list = []
    for rownum,row in enumerate(data,1):
        import_list.append(ImportRecord(row,headers,rownum))
    return import_list

# Airtable functions
def initialize_airtable() -> Base:
    """Find access key in current directory, connect to airtable, 
       and retrieve the database object

    Returns:
        Base object: the KGSA database object
    """
    # ============ Access Key Filename and Location ============
    access_key_filename = '.abaldwin-kgsa-airtable-token.txt'
    access_key_path = os.curdir

    # ============ KGSA Database ID (Airtable "Base ID") ============
    base_id ='appMeePQqolbGWgZx'

    # ---- Connect to Airtable ----
    with open(f"{access_key_path}/{access_key_filename}", "r", encoding="UTF-8") as file:
        access_key = file.read()
    access_key = str(access_key)
    access_key = access_key.strip()
    api = Api(access_key)
    b = api.base(base_id)
    return b

def get_field_options(field:FieldSchema) -> List[str]:
    allowed_values = field.options.choices
    return_list = []
    for val in allowed_values:
        return_list.append(val.name)
    return return_list

# Student functions
def get_students_from_grad_year(fields:List[str],students_table:Table) -> Optional[Tuple[List[RecordDict],str]]:
    grad_yr_field = students_table.schema().field('Grad Class')
    grad_yr_options = get_field_options(grad_yr_field)
    print('Please select the graduating class year for the students you are importing:')
    selected_grad_yr = user_selection(grad_yr_options)
    if selected_grad_yr == 'quit':
        return None
    else:
        formula = formulas.match({'Grad Class': selected_grad_yr})
        records = students_table.all(fields=fields, formula=formula)
        return (records, selected_grad_yr)

def get_next_at_student_id(grad_year:str,students:List[RecordDict]) -> int:
    try:
        max_id = max(student['fields']['ID'] for student in students)
        next_id = max_id+1
    except:
        max_id = 0
    if max_id == 0 or max_id == '' or max_id == 'None':
        next_id = (int(grad_year)-2000)*100
    return next_id

def find_match_by_znum(record:ImportRecord, students:List[RecordDict]) -> ImportRecord:
    record.match_type = 'no match'
    #check for znum match
    try:
        input_znum = int(record.get('zeraki_num'))
    except ValueError:
        # invalid zeraki num in import
        print(f"Zeraki number in import csv should be a numeric value. No match possible by Zeraki Num.")
        return record

    # search airtable data for matching zeraki num, grad class, name
    for student in students:
        try:
            at_znum = int(student['fields']['Zeraki ADM No'])
        except (KeyError, ValueError):
            # no zeraki num or invalid num in db so continue to next student
            continue
        
        if input_znum == at_znum:
            record.at_id = student['fields']['ID']
            record.match_type = 'adm no'
            record.matched_record = student
            try:
                record.grad_year = student['fields']['Grad Class']
            except KeyError:
                pass

            #check for exact match
            db_first_name = student['fields']['First name']
            db_last_name = student['fields']['Last name']
            if record.name('first') == db_first_name and record.name('last') == db_last_name:
                record.match_type = 'exact'
                print(f"Found exact match by Zeraki Num {input_znum} and Name for Student ID {record.at_id} - {record.name()}.")
                print("")
                return record
            else:
                print(f"Found match by Zeraki Num {input_znum} to Student ID {record.at_id} - {db_first_name} {db_last_name}.")
                print("")
                return record
    print(f"No matches found by Zeraki Number {input_znum} - {record.name()}.")
    print("")
    return record

def find_match_by_name(record:ImportRecord, students:List[RecordDict]) -> ImportRecord:
    match_outcome_list = []
    for student in students:
        match_type = 'no match'
        db_first_name = student['fields']['First name'].upper()
        db_last_name = student['fields']['Last name'].upper()

        # Automatically match and return full name matches
        if record.name('first') == db_first_name and record.name('last') == db_last_name:
            match_type = 'full name'
            record.matched_record = student
            record.at_id = record.matched_record['fields']['ID']
            record.match_type = match_type
            try:
                record.grad_year = student['fields']['Grad Class']
            except KeyError:
                pass
            print(f"Found {record.get('match_type')} match for Student ID {record.at_id} - {record.name()}")
            print("")
            return record

        #set other match types
        elif record.name('last') == db_last_name:
            match_type = 'last name'
        elif record.name('first') == db_first_name:
            match_type = 'first name'
        else:
            # check if any of their names match, regardless of order
            db_name_list = db_first_name.split(' ')+db_last_name.split(' ')
            csv_name_list = record.name().split(' ')
            common_names = [item for item in db_name_list if item in csv_name_list]
            if len(common_names)> 0:
                match_type = 'common name'
        
        # add each potential match (besides full name matches) to a selection list
        try:
            match_outcome_list.append((student,match_type,f"Student ID: {student['fields']['ID']}: First name: {db_first_name} Last name: {db_last_name}"))
        except UnboundLocalError: #if match_type isn't set, it's not a match so skip to the next student
           continue
        
    # loop through match types in order of likely accuracy
    for match_type in ['last name','first name','common name','no match']:
        match_options = [m[2] for m in match_outcome_list if m[1] == match_type]
        match_options.append('None of these are a match')

        # print to user why the listed students are possible matches
        if len(match_options) > 1:
            if match_type == 'no match':
                print(f"The following Airtable records have no names in common with {record.name()}. However, please select if any of these is a correct match for this student:")
            else:
                print(f"The following Airtable records have a {match_type} that matches student {record.name()}. Please select which one is a correct match for this student:")
            
            #ask user for selection to confirm student match
            selected_record_text = user_selection(match_options,quit_allowed=True)
            if selected_record_text == 'quit':
                return 'quit'

            #handle user selection
            selected_record_list = [m for m in match_outcome_list if selected_record_text == m[2]]
            if len(selected_record_list) > 1:
                raise DuplicateRecordError
            elif len(selected_record_list) == 1:
                record.matched_record = selected_record_list[0][0]
                record.at_id = record.matched_record['fields']['ID']
                record.match_type = match_type
                try:
                    record.grad_year = student['fields']['Grad Class']
                except KeyError:
                    pass
                #print(f"Match found by {match_type} for student {str(record)}")
                return record
    print(f"No matches found by name for student {record.name()}.")
    print("")
    return record

def convert_numeric_values(table:Table,field_dict:dict):
    for key,val in field_dict.items():
        field = table.schema().field(key)
        if field.type  == 'number':
            field_dict[key] = int(val)

    return field_dict

def check_field_errors(input:dict,output:RecordDict) -> True:
    errors = []
    for key in output['fields'].keys():
        if key in input.keys():
            if input[key] != output['fields'][key]:
                errors.append(key)
    if len(errors) > 0:
        err_str = ", ".join(errors)
        print(f"The following fields for Student ID {output['fields']['ID']} could not be imported: {err_str}")
        return True
    else:
        return False

def update_student(student_record:RecordDict,fields_to_update:dict,students_table:Table) -> bool:
    at_record_id = student_record['id']

    fields_to_update = convert_numeric_values(students_table,fields_to_update)
    try:
        updated_student = students_table.update(at_record_id,fields_to_update)
    except:
         print(f"Unable to update Student ID {student_record['fields']['ID']} with {str(fields_to_update)}")
         return False
    if check_field_errors(fields_to_update,updated_student):
        return False
    else:
        print(f"Successfully updated Student ID {student_record['fields']['ID']} with {str(fields_to_update)}")
        return True

def create_student(student_dict:dict,students_table) -> RecordDict:
    student_dict = convert_numeric_values(students_table,students_table)
    try:
        created_student = students_table.create(student_dict)
        print(f"Successfully created Student ID {created_student['fields']['ID']} with Student details: {str(student_dict)}")
        return created_student
    except Exception:
        print(f"Unable to create Student with Student details: ")
        print_dict(student_dict)
        return False

def import_students(import_data:List[ImportRecord],student_records:List[RecordDict],grad_year:str,students_table:Table,test_flag:bool=True):
    count_total = 0
    count_updated = 0
    count_created = 0

    # Get next available airtable ID for the relevant student records
    at_student_id = get_next_at_student_id(grad_year,student_records)

    # loop through Import Records
    for import_record in import_data:
        print(f"""
--------
Now importing CSV row {import_record.get('csv_row')}...
        """)
        import_outcome = None

        # find if student already exists
        import_record = find_match_by_znum(import_record,student_records)

        if import_record.match_type == 'no match':
            import_record = find_match_by_name(import_record,student_records)
            if import_record =='quit':
                break

        # create NEW STUDENT if no match found    
        if import_record.get('match_type') == 'no match':
            print(f"")
            print(f"No match was found.")
            print(f"Would you like to create an Airtable record with the following data:")
            print_dict(import_record.return_import_dict())
            print('Please select Y/N:')
            choice = user_selection(options_list=['Yes','No'],quit_allowed=True)
            if choice == 'quit':
                print(f"Quitting program...")
                break
            if choice == 'No':
                print(f"Skipping student...")
                continue
            student_template = import_record.return_import_dict(at_student_id)
            if test_flag == True:
                import_outcome = True
            else:
                created_student = create_student(student_template,students_table)
                if isinstance(created_student,RecordDict):
                    import_outcome = True # if record was created, import was successful enough that the at ID should be incremented
                    check_field_errors(student_template, created_student)
            if import_outcome == True:
                import_record.at_id = at_student_id
                import_record.at_edit_type = 'new'
                count_created += 1
                at_student_id += 1
            # else:
            #     print(f"Failed to Create Student: {str(import_record)}, skipping student...") 

        # optionally UPDATE STUDENT if partial match
        else:
            csv_fields = import_record.return_import_dict()
            db_student = import_record.matched_record
            db_fields = db_student['fields']
            keys_to_update = compare_students(csv_fields,db_fields)
            if len(keys_to_update) < 1:
                print(f"No data to updated on Student Record {db_fields['ID']}, skipping student.")
                continue
            fields_to_import = {}

            # get user input on which fields to update
            for key in keys_to_update:
                print(f"Would you like to update the students {key} in Airtable?")
                print('Please select Y/N:')
                choice = user_selection(options_list=['Yes','No'])
                if choice == 'No':
                    pass
                else:
                    fields_to_import[key] = csv_fields[key]
            
            # move forward with updating the student record
            if test_flag == True:
                import_outcome = True
            else:
                import_outcome = update_student(db_student,fields_to_import,students_table)
            if import_outcome == True:
                import_record.at_edit_type = 'edit'
                count_updated += 1
            # else:
            #     print(f"Failed to Update Student with CSV data: {str(fields_to_import)}, skipping student...")

        if test_flag:
            print(f"Test mode - no actual import completed")

    return count_total, count_created, count_updated

# Grades functions
def import_grades():
    # TODO get input from user about grade type
    print("Grade imports not yet supported, quitting program.")
    return False

def main_import(test=True):
    """Main program that calls user input functions and import functions

    Returns:
        bool: True if import successful, False otherwise
    """
    print("Welcome to the KGSA Airtable import tool.")

    # DETERMINE TYPE OF IMPORT
    print("Please choose what type of data you are importing from Zeraki:")
    import_type_options = ['Students and KCPEs','Term Grades']
    import_type = user_selection(import_type_options)
    #import_type = select_import_type()
    if import_type == 'quit':
        return False
    elif import_type in import_type_options:
        # Select CSV to import
        selected_file = select_file()
        if selected_file == None:
            return False

        # PARSE CSV IMPORT DATA
        # Parse and Validate CSV
        import_list = csv_to_import_records(selected_file)
            
        # PULL RELEVANT RECORDS AND FIELDS FROM DB
        # Connect to Airtable Table: Students
        b = initialize_airtable()
        students_table = b.table('Students')
        if import_type == import_type_options[0]:
            # limit the fields returned
            student_import_fields = ['ID','First name','Last name','Grad Class','Zeraki ADM No','KCPE Score']
            # limit the records returned by grad year
            filtered_students = get_students_from_grad_year(student_import_fields,students_table)
            if filtered_students == None:
                return False
            else:
                student_records, grad_year = filtered_students

            # IMPORT STUDENT DATA
            #import data and print outcome
            total, created, updated = import_students(import_list,student_records,grad_year,students_table,test)
            print(f"Out of {total} total CSV students, {created} new student records were created and {updated} student records were updated.")
            return True

        elif import_type == import_type_options[1]:
            print('Grades import not supported yet, quitting program.')
            return False
        else:
            print("Invalid import type, shouldn't ever get to this code, quitting program.")
            return False
    else:
        print("Invalid import type, quitting program.")
        return False

def parse_args():
    parser = argparse.ArgumentParser(description="Choose a function to run")
    parser.add_argument(
        "-f","--function",
        choices=["test","import"],
        default="test",
        help="Specify which function to run: 'test','real'"
    )
    return parser.parse_args()

def main():
    args = parse_args()

    # Run the appropriate function based on the argument
    if args.function == "test":
        main_import(test=True)
    else:
        main_import(test=False)

if __name__ == "__main__":
    main()
