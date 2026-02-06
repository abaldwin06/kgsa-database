import os
import csv
from typing import List, Tuple, Optional, TextIO, Literal
from pyairtable import Api, formulas, Table, Base
from pyairtable.api.types import RecordDict
from pyairtable.models.schema import FieldSchema, TableSchema
from requests.exceptions import HTTPError
import argparse
import json
from datetime import datetime
import openpyxl
import re

class DuplicateRecordError(Exception):
    pass

class UserQuitOut(Exception):
    pass

class ImportRecord:
    # properties:
    # csv_row, zeraki_num, zeraki_name, kcpe, first_name, last_name, at_id, match_type, matched_record, at_edit type
    # grades array of structs with {subj: 'HIS', str: 'B',num: 80}, test_type, test_date, form 
    def __init__(self,row:List,headers:List,csv_row_num:int) -> bool:
        self.csv_row = csv_row_num
        self.grades = []
        self.grades.append({'subj':'Overall', 'str': None, 'num': None})
        for idx,header in enumerate(headers):
            if header == 'ADMNO':
                self.zeraki_num = int(row[idx])
            elif header == 'NAME':
                self.zeraki_name = row[idx].upper().strip()
                self.parse_names()
            elif header == 'KCPE':
                try:
                    self.kcpe = int(row[idx])
                except ValueError:
                    pass
            elif header == 'TT PTS':
                try:
                    self.grades[0]['num'] = float(row[idx])
                    print(f"Student {self.zeraki_name} has an overall numeric grade of {float(row[idx])}.")
                except ValueError:
                    print(f"numeric grade expected for TT PTS")
                    pass
                except (IndexError,KeyError):
                    print(f"corrupt grades property in import record for znum {self.get('zeraki_num')}")
                    pass
            elif header == 'GR':
                try:
                    self.grades[0]['str'] = str(row[idx])
                    print(f"Student {self.zeraki_name} has an overall grade of {str(row[idx])}.")
                except ValueError:
                    print(f"string grade expected for GR")
                    pass
                except (IndexError,KeyError):
                    print(f"corrupt grades property in import record for znum {self.get('zeraki_num')}")
                    pass
            elif header in ['ENG','KIS','MAT','BIO','PHY','CHE','HIS','GEO','CRE','IRE','BST']:
                self.add_grade(header,str(row[idx]))

    def match_to_at_student(self,students:List[RecordDict],verbose:bool=False):
        # MATCH BY ZERAKI NUM
        # if student not already matched
        if self.get('at_id') == None:
            self.match_type = 'no match'
            
            # search airtable data for matching zeraki num, grad class, name
            for student in students:
                try:
                    at_znum = int(student['fields']['Zeraki ADM No'])
                except (KeyError, ValueError):
                    # no zeraki num or invalid num in db so continue to next student
                    continue
                
                if self.get("zeraki_num") == at_znum:
                    self.at_id = student['fields']['ID']
                    self.at_rec_id = student['id']
                    self.match_type = 'adm no'
                    self.matched_record = student
                    try:
                        self.grad_year = student['fields']['Grad Class']
                    except KeyError:
                        pass

                    #check for exact match
                    db_first_name = student['fields']['First name']
                    db_last_name = student['fields']['Last name']
                    db_first_name = db_first_name.upper().strip()
                    db_last_name = db_last_name.upper().strip()
                    if self.name('first') == db_first_name and self.name('last') == db_last_name:
                        self.match_type = 'exact'
                        if verbose:
                            print(f"Found exact match by Zeraki Num {self.zeraki_num} and Name for Student ID {self.at_id} - {self.name()}.")
                            print("")
                        return self.at_id
                    else:
                        if verbose:
                            print(f"Found match by Zeraki Num {self.zeraki_num} to Student ID {self.at_id} - {db_first_name} {db_last_name}.")
                            print("")   
                        return True
            if verbose:
                print(f"No matches found by Zeraki Number {self.zeraki_num} - {self.name()}.")
                print("")
            # MATCH BY NAME AS FALLBACK
            return False
        else:
            return self.get('at_id')

    def add_grade(self,subj:str,csv_grade:str):
        if (subj not in ('TT PTS','GR')) and csv_grade != "":
            grade_num = None
            grade_str = None
            grade_vals = csv_grade.split(" ")
            for grade in grade_vals:
                try:
                    grade_num = int(grade)
                except:
                    grade_str = grade
            if grade_num is None and grade_str is None:
                print(f"CSV row {self.csv_row} student {self.zeraki_name} has null grades for {subj}. Skipping...")
            elif grade_num == None:
                self.grades.append({
                    'subj':subj,
                    'str':grade_str
                        })
                print(f"CSV row {self.csv_row} student {self.zeraki_name} has a {grade_str} grade for {subj}.")
            elif grade_str == None:
                self.grades.append({
                    'subj':subj,
                    'num':grade_num
                        })
                print(f"CSV row {self.csv_row} student {self.zeraki_name} has a {grade_num} grade for {subj}.")
            else:
                self.grades.append({
                                    'subj':subj,
                                    'str':grade_str,
                                    'num':grade_num
                                    })
                print(f"CSV row {self.csv_row} student {self.zeraki_name} has a {grade_str} grade with {grade_num} pts for {subj}.")

    def add_test_type(self,test_type:str,form:str,test_date_str:str,grad_year:str):
        self.test_type = test_type #user input should have already validated test type matches Airtable vals
        self.form = form #user input should have already validated form value matches Airtable vals
        self.grad_year = grad_year #user input should have already validated grad year matches Airtable vals
        self.test_date = test_date_str #need to reformat for import to airtable
        return True

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
    Zeraki ADM No: {self.get('zeraki_num')}"""
        except TypeError:
            pass
        try:
            text = text + f"""
    Matched by {self.get('match_type')} to Airtable ID: {self.get('at_id')}"""
        except TypeError:
            pass
        try:
            text = text + f"""
    Student: {self.name()} from {self.grad_year}"""
        except TypeError:
            #shouldn't happen
            pass
        try:
            text = text + f"""
    KCPE score: """+ str(self.get('kcpe'))
        except TypeError:
            pass
        try:
            text = text + f"""
    {self.test_date} - {self.form} {self.test_type} test results for {len(self.grades) - 1} subjects """
        except:
            pass
        return text

    def parse_names(self):
        try:
            names = self.get('zeraki_name').upper().split(' ')
        except TypeError:
            print(f"Row {self.get('csv_row')}: Error splitting Student Name, no Zeraki Name present, skipping student.")
            return
        name_count = len(names)
        if name_count < 2:
            print(f"Row {self.get('csv_row')}: Error splitting Student Name, unexpected number of names: {self.get('zeraki_name')}.")
        else:
            self.first_name = names[0].strip().upper()
            self.last_name = " ".join(names[1:]).strip().upper()
            #print(f"Row {self.csv_row}: First name: {self.first_name}, Last name: {self.last_name}.")
    
    def print_grades(self):
        for grade in self.grades:
            print(f"""        {grade['subj']}: {grade['str']} {grade['num']}""")

    def return_grades_import_list(self):
        import_list = []

        for grade in self.grades:
            grade_dict = {}
            grade_dict['Student ID'] = [self.at_rec_id]
            grade_dict['Date of Score']= self.test_date, #TODO is this a mistake? 
            grade_dict['Form'] = self.form
            grade_dict['Score Type'] = self.test_type
            grade_dict['Date of Score']= self.test_date
            grade_dict['Subject'] = grade['subj']
            grade_dict['Letter Score'] = grade['str']
            try:
                grade_dict['Numeric Score'] = grade['num']
            except KeyError:
                pass
            import_list.append(grade_dict)
        return import_list

    def return_student_import_dict(self,at_id=None,grad_year=None):
        import_dict = {}
        if self.get('at_id'):
            import_dict['ID'] = self.get('at_id')
        elif at_id != None:
            import_dict['ID'] = at_id
        import_dict['Zeraki ADM No'] = self.get('zeraki_num')
        import_dict['First name'] = self.name('first').title()
        import_dict['Last name'] = self.name('last').title()
        if self.get('grad_year'):
            import_dict['Grad Class'] = self.get('grad_year')
        elif grad_year != None:
            import_dict['Grad Class'] = grad_year
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
        if user_quitting(user_choice) and quit_allowed == True:
            print("Quitting the program.")
            raise UserQuitOut
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
    selected_file_name = user_selection(files) #could raise UserQuitOut

    # Full path of the selected file
    selected_file_path = os.path.join(folder_name, selected_file_name)
    selected_file = open(selected_file_path,mode="r",newline='')
    return selected_file

def print_dict(d:dict):
    print(json.dumps(d, indent=4))

def compare_records(csv_data:dict,db_data:dict):
    keys_to_update = []
    comparison_text = "Proposed updates to the DB:"
    for key,csv_val in csv_data.items():

        # DATA TO BE ADDED
        if key not in db_data.keys():
            comparison_text = comparison_text + f"\n -add-  {key}: {csv_val}"
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
                comparison_text = comparison_text + f"\n        {key}: {db_val}"

            # DATA TO BE UPDATED
            else:    
                comparison_text = comparison_text + f"\n -edit- {key}: {db_data[key]} -> {csv_val}"
                keys_to_update.append(key)
    
    if len(keys_to_update) > 0:
        print(comparison_text + "\n")
    else:
        print("No differences between import data and existing record.\n")

    return keys_to_update

def user_quitting(input:str):
    if isinstance(input,str) and input.upper() in ['Q','QUIT','EXIT','OPT','STOP']:
        return True
    else:
        return False

def get_date_from_user():
    while True:
        user_input = input("Enter a date (YYYY-MM-DD): ")
        try:
            date_obj = datetime.strptime(user_input, "%Y-%m-%d").date()
            return date_obj.strftime("%Y-%m-%d")  # Return as a formatted string
        except ValueError:
            if user_quitting(user_input):
                print("Quitting Program...")
                raise UserQuitOut
            else:
                print("Invalid format. Please enter a valid date in YYYY-MM-DD format.")


def get_grade_import_details(scores_schema:TableSchema, import_list:List[ImportRecord], grad_year:str) -> Optional[Tuple[str]]:
    # column IDs for Test Scores Table
    test_date_col = get_field_from_table(scores_schema,'fldYmomAHoRF6mQUQ') #Name of AT Column: Date of Score
    form_col = get_field_from_table(scores_schema,'fldf2lj8I78aQnUoh') #Name of AT Column: Form
    test_type_col= get_field_from_table(scores_schema,'fldzfmDP86VoOPPb4') #Name of AT Column: Score Type

    # get score type
    print('What type of test scores are in the file to be imported?')
    test_type = user_selection(get_field_options(test_type_col),True) #Could raise UserQuitOut

    # get which form the student was in
    if test_type == 'KCSE':
        form = "Form 4"
    else:
        print('This exam was taken while the students were in what form?')
        form = user_selection(get_field_options(form_col),True)  #Could raise UserQuitOut

    print('On what date was this exam taken?')
    test_date_str = get_date_from_user()  #Could raise UserQuitOut
    
    for rec in import_list:
        rec.add_test_type(test_type,form,test_date_str,grad_year)

    return import_list


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

def get_field_from_table(table_schema,field_id):
    matched_fields = [field for field in table_schema.fields if field.id == field_id] 
    if len(matched_fields) == 0:
        raise ValueError(f'No field by the id of {field_id} in table {table_schema.name}')
    else:
        return matched_fields[0]

# Student functions
def get_students_from_grad_year(fields:List[str],students_table:Table,grad_year:str) -> Optional[Tuple[List[RecordDict],str]]:
    grad_yr_field = students_table.schema().field('Grad Class')
    grad_yr_options = get_field_options(grad_yr_field)
    if grad_year not in grad_yr_options:
        print('Please select the graduating class year for the students you are importing:')
        selected_grad_yr = user_selection(grad_yr_options) # Could Raise UserQuitOut
    else:
        selected_grad_yr = grad_year

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

def find_match_by_name(record:ImportRecord, students:List[RecordDict]) -> ImportRecord:
    match_outcome_list = []
    for student in students:
        match_type = 'no match'
        db_first_name = student['fields']['First name'].upper().strip()
        db_last_name = student['fields']['Last name'].upper().strip()

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
            selected_record_text = user_selection(match_options,quit_allowed=True) #could raise UserQuitOut

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

def convert_numeric_values(table:Table,fields_to_import:dict):
    for key,val in fields_to_import.items():
        field = table.schema().field(key)
        if field.type  == 'number':
            fields_to_import[key] = int(val)

    return fields_to_import

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

def create_student(student_to_create:dict,students_table:Table) -> RecordDict:
    student_to_create = convert_numeric_values(students_table,student_to_create)
    try:
        created_student = students_table.create(student_to_create)
        print(f"Successfully created Student ID {created_student['fields']['ID']} with Student details: {str(created_student['fields'])}")
        return created_student
    except Exception:
        print(f"Unable to create Student with Student details: ")
        print_dict(student_to_create)
        return False

def create_grade(grade_dict:dict,grade_table) -> RecordDict:
    #grades_dict = convert_numeric_values(students_table,students_table)
    try:
        created_grade = grade_table.create(grade_dict)
        print(f"Successfully created Grade ID {created_grade['fields']['Score ID']} with details: {str(grade_dict)}")
        return created_grade
    except HTTPError as e:
         print(f"Unable to create Grade with details: ")
         print_dict(grade_dict)
         print(e)
         return False

def update_grade(grade_dict:dict,grade_to_update:str,grade_table):
    try:
        updated_grade = grade_table.update(grade_to_update,grade_dict)
        print(f"Successfully updated Grade ID {updated_grade['fields']['Score ID']} with details: {str(grade_dict)}")
        return updated_grade
    except HTTPError as e:
         print(f"Unable to update Grade with details: ")
         print_dict(grade_dict)
         print(e)
         return False

def remind_if_test_mode(test_flag,reminder_before_import:bool=True):
    if test_flag:
        if reminder_before_import:
            print(f"Reminder - importing in Test Mode - no actual import will be completed.")
        else:
            print(f"Test mode - no actual import completed".upper())

def import_students(import_data:List[ImportRecord],student_records:List[RecordDict],grad_year:str,students_table:Table,test_flag:bool=True):
    count_total = 0
    count_updated = 0
    count_created = 0

    # Get next available airtable ID for the relevant student records - in case a new record is needed
    at_student_id = get_next_at_student_id(grad_year,student_records)

    # loop through Import Records
    for import_record in import_data:
        print(f"""
--------
Now importing CSV row {import_record.get('csv_row')}...
        """)
        import_outcome = None

        # match to existing student by ZNum
        import_record.match_to_at_student(student_records)

        # match to existing student by Name
        if import_record.match_type == 'no match':
            try:
                import_record = find_match_by_name(import_record,student_records)
            except UserQuitOut:
                print(f"Quitting program...")
                break

        # create NEW STUDENT if no match found    
        if import_record.get('match_type') == 'no match':
            print(f"")
            print(f"No match was found.")
            print(f"Would you like to create an Airtable record with the following data:")
            student_template = import_record.return_student_import_dict(at_student_id,grad_year)
            print_dict(student_template)
            remind_if_test_mode(test_flag)
            print('Please select Y/N:')
            try:
                choice = user_selection(options_list=['Yes','No'],quit_allowed=True)
            except UserQuitOut:
                print(f"Quitting program...")
                break
            if choice == 'No':
                print(f"Skipping student...")
                continue
            remind_if_test_mode(test_flag,False)
            if test_flag == True:
                import_outcome = True
            else:
                created_student = create_student(student_template,students_table)
                if created_student != False:
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
            csv_fields = import_record.return_student_import_dict()
            db_student = import_record.matched_record
            db_fields = db_student['fields']
            keys_to_update = compare_records(csv_fields,db_fields)
            if len(keys_to_update) == 0:
                print(f"No data to update on Student Record {db_fields['ID']}, skipping student.")
                continue
            fields_to_import = {}

            # get user input on which fields to update
            quit=False
            for key in keys_to_update:
                print(f"Would you like to update the students {key} in Airtable?")
                remind_if_test_mode(test_flag)
                print('Please select Y/N:')
                try:
                    choice = user_selection(options_list=['Yes','No']) #could raise UserQuitOut
                except UserQuitOut:
                    quit=True
                    break
                if choice == 'No':
                    pass
                else:
                    fields_to_import[key] = csv_fields[key]
            if quit:
                break

            # move forward with updating the student record
            if test_flag == True:
                if len(fields_to_import) == 0:
                    print("No fields to update, skipping...")
                else:
                    import_outcome = True
            else:
                if len(fields_to_import) == 0:
                    print("No fields to update, skipping...")
                else:
                    import_outcome = update_student(db_student,fields_to_import,students_table)
            if import_outcome == True:
                import_record.at_edit_type = 'edit'
                count_updated += 1
            # else:
            #     print(f"Failed to Update Student with CSV data: {str(fields_to_import)}, skipping student...")

        remind_if_test_mode(test_flag,False)
        # if test_flag:
        #     print(f"Test mode - no actual import completed".upper())

    return count_total, count_created, count_updated

def convert_xlsx_with_openpyxl(xlsx_file, csv_file):
    """
    Converts a single sheet of an XLSX file to a CSV file,
    skipping the first row (header).
    """
    wb = openpyxl.load_workbook(
        xlsx_file,
        read_only=True,
        data_only=True
    )

    sh = wb.active # Get the active worksheet

    rows = sh.iter_rows(values_only=True)

    # Skip the first row (header)
    next(rows, None)

    with open(csv_file, 'w', newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([
                value if value is not None else ""
                for value in row
            ])

    print(f"Successfully converted '{xlsx_file}' to '{csv_file}'")

def get_filename_from_user(original_file_name):
    """
    Gets information from user to determine standardized file name for CSV
    """
    years = [
        "2012", "2013", "2014", "2015", "2016", "2017", "2018",
        "2019", "2020", "2021", "2022", "2023", "2024", "2025",
        "2026", "2027", "2028"
    ]
    forms = ["Form 1", "Form 2", "Form 3", "Form 4"]
    test_types = [
        "KCSE",
        "Term 1 - Entry",
        "Term 1 - Mid Term",
        "Term 1 - End Term",
        "Term 1 - Other",
        "Term 2 - Entry",
        "Term 2 - Mid Term",
        "Term 2 - End Term",
        "Term 2 - Other",
        "Term 3 - Entry",
        "Term 3 - End Term",
        "Term 3 - Mid Term",
    ]
    test_dates = {
        "2021": {
            "Term 1 - Entry": "2021-07-26",
            "Term 1 - Mid Term": "2021-08-28",
            "Term 1 - End Term": "2021-10-01",
            "Term 2 - Entry": "2021-10-11",
            "Term 2 - Mid Term": "2021-11-16",
            "Term 2 - End Term": "2021-12-23",
            "Term 3 - Entry": "2022-01-03",
            "Term 3 - Mid Term": "2022-02-03",
            "Term 3 - End Term": "2022-03-04",
        },
        "2022": {
            "Term 1 - Entry": "2022-04-25",
            "Term 1 - Mid Term": "2022-05-28",
            "Term 1 - End Term": "2022-07-01",
            "Term 2 - Entry": "2022-07-11",
            "Term 2 - Mid Term": "2022-08-13",
            "Term 2 - End Term": "2022-09-16",
            "Term 3 - Entry": "2022-09-26",
            "Term 3 - Mid Term": "2022-10-25",
            "Term 3 - End Term": "2022-11-25",
        },
        "2023": {
            "Term 1 - Entry": "2023-01-23",
            "Term 1 - Mid Term": "2023-03-09",
            "Term 1 - End Term": "2023-04-21",
            "Term 2 - Entry": "2023-05-08",
            "Term 2 - Mid Term": "2023-06-24",
            "Term 2 - End Term": "2023-08-11",
            "Term 3 - Entry": "2023-08-28",
            "Term 3 - Mid Term": "2023-09-30",
            "Term 3 - End Term": "2023-11-03",
        },
        "2024": {
            "Term 1 - Entry": "2024-01-08",
            "Term 1 - Mid Term": "2024-02-21",
            "Term 1 - End Term": "2024-04-05",
            "Term 2 - Entry": "2024-04-29",
            "Term 2 - Mid Term": "2024-06-15",
            "Term 2 - End Term": "2024-08-02",
            "Term 3 - Entry": "2024-08-26",
            "Term 3 - Mid Term": "2024-09-25",
            "Term 3 - End Term": "2024-10-25",
        },
        "2025": {
            "Term 1 - Entry": "2025-01-06",
            "Term 1 - Mid Term": "2025-02-19",
            "Term 1 - End Term": "2025-04-04",
            "Term 2 - Entry": "2025-04-28",
            "Term 2 - Mid Term": "2025-06-14",
            "Term 2 - End Term": "2025-08-01",
            "Term 3 - Entry": "2025-08-25",
            "Term 3 - Mid Term": "2025-09-24",
            "Term 3 - End Term": "2025-10-24",
        },
        "2026": {
            "Term 1 - Entry": "2026-01-12",
            "Term 1 - Mid Term": "2026-02-25",
            "Term 1 - End Term": "2026-04-02",
            "Term 2 - Entry": "2026-04-27",
            "Term 2 - Mid Term": "2026-06-24",
            "Term 2 - End Term": "2026-07-31",
            "Term 3 - Entry": "2026-08-24",
            "Term 3 - Mid Term": "2026-09-15",
            "Term 3 - End Term": "2026-10-23"
        }
    }
    while True:
        # get score type
        print('Class of...')
        grad_year = user_selection(years,True) #Could raise UserQuitOut
        print('Take while in form...')
        form = user_selection(forms,True) #Could raise UserQuitOut
        print('Exam taken during calendar year...')
        year_of_exam = user_selection(years,True)  #Could raise UserQuitOut
        print('Type of exam...')
        test_type = user_selection(test_types,True)  #Could raise UserQuitOut
        if test_type == 'KCSE':
            test_date = f'{year_of_exam}-11-20'
        else:
            test_date = test_dates[year_of_exam][test_type]

        print(f'Original file name is {original_file_name} ')
        new_file_name = f'./to-import/C{grad_year} - {test_type} - {form} - {test_date}.csv'
        print(f'{new_file_name}')
        return new_file_name

def parse_standard_filename(filename):
    """
    Parse standardized KGSA exam CSV filename.

    Expected format:
    C{grad_year} - {test_type} - {form} - {test_date}.csv

    Returns:
        grad_year (str)
        test_type (str)
        form (str)
        test_date (str)

    Raises:
        ValueError if filename does not match expected format
    """

    base = os.path.basename(filename)

    pattern = (
        r"^C(?P<grad_year>\d{4})\s-\s"
        r"(?P<test_type>.+?)\s-\s"
        r"(?P<form>Form\s[1-4])\s-\s"
        r"(?P<test_date>\d{4}-\d{2}-\d{2})\.csv$"
    )

    match = re.match(pattern, base)
    if not match:
        raise ValueError(f"Filename does not match expected format: {base}")

    grad_year = match.group("grad_year")
    test_type = match.group("test_type")
    form = match.group("form")
    test_date = match.group("test_date")

    return grad_year, test_type, test_date, form

# Grades functions
def import_grades(import_data:List[ImportRecord],student_records:List[RecordDict],grd_tbl:Table,test_flag:bool=True):
    print("")
    print(f"Would you like to check for duplicates and approve each grade before importing?")
    remind_if_test_mode(test_flag)
    print('Please select Y/N:')
    choice = user_selection(options_list=['Yes','No'],quit_allowed=True) #could raise UserQuitOut
    if choice == 'Yes':
        approve_each_and_dup_check = True
    else:
        approve_each_and_dup_check = False

    # keep track of number of student records updated, grades created
    count_unmatched_students = 0
    count_matched_students = 0
    count_imported_grades = 0
    count_imported_with_errors = 0

    # Loop through import data
    for import_rec in import_data:
        import_rec.match_to_at_student(student_records)
        if import_rec.get('at_id') == None:
            print(f"No airtable record found for student {import_rec.name()}. Skipping...")
            count_unmatched_students+=1
            continue
        else:
            count_matched_students+=1
        grade_list = import_rec.return_grades_import_list()
        for grade in grade_list:
            found_dup = False

            if approve_each_and_dup_check:
                # Check for a duplicate grade record
                for grd in grd_tbl.all():
                    try:
                        #TODO test change this to check for test type not date
                        if grd['fields']['Student ID'] == grade['Student ID'] and grd['fields']['Score Type'] == grade['Score Type'] and grd['fields']['Form'] == grade['Form'] and grd['fields']['Subject'] == grade['Subject']:

                            print(f"There is already a {grade['Subject']} grade for student {import_rec.name()} for a {grade['Form']} {grade['Score Type']} exam:")
                            keys_to_update = compare_records(grade,grd['fields'])
                            found_dup = True
                            dup_grade = grd['id']
                            break
                    except KeyError:
                        continue

                if found_dup and len(keys_to_update)>0:
                    print(f"Would you like to update the Airtable record with the data above?")
                elif found_dup==False:
                    print(f"Would you like to create an Airtable record with the following data:")
                    print_dict(grade)
                else:
                    choice="No"
                    print("Skipping grade because of duplicate... \n")
                    continue
                remind_if_test_mode(test_flag)
                print('Please select Y/N:')
                try:
                    choice = user_selection(options_list=['Yes','No'],quit_allowed=True)
                except UserQuitOut:
                    print_grade_import_summary(count_imported_grades,count_matched_students,count_unmatched_students)
                    raise UserQuitOut
            else:
                choice = "Yes"
            if choice == 'No':
                print(f"Skipping grade...")
                continue
            if test_flag == True:
                count_imported_grades += 1
            else:
                if found_dup:
                    created_grade = update_grade(grade,dup_grade,grd_tbl)
                else:
                    created_grade = create_grade(grade,grd_tbl)
                if created_grade == False:
                    print("Failed to import record.")
                else:
                    if check_field_errors(grade, created_grade):
                        count_imported_with_errors+=1
                    else:
                        count_imported_grades += 1

    print_grade_import_summary(count_imported_grades,count_matched_students,count_unmatched_students)
    return True

def print_grade_import_summary(count_imported_grades,count_matched_students,count_unmatched_students):
    print(f"{count_imported_grades} grades imported for {count_matched_students} students.")
    if count_unmatched_students > 0:
        print(f"Grades not imported for {count_unmatched_students} due to not being able to match to a student record in Airtable")

def main_import(test=True):
    """Main program that calls user input functions and import functions

    Returns:
        bool: True if import successful, False otherwise
    """
    print("Welcome to the KGSA Airtable import tool.")

    # DETERMINE TYPE OF IMPORT
    print("Please choose what type of data you are importing from Zeraki:")
    import_type_options = ['Students and KCPEs','Grades']
    try:
        import_type = user_selection(import_type_options,True)
    except UserQuitOut:
        return False

    if import_type in import_type_options:
        # Select CSV to import
        try:
            selected_file = select_file()
        except UserQuitOut:
            return False

        if selected_file.name.endswith('.csv'):
            # PARSE CSV IMPORT DATA

            # Parse key fields from standard filenaming structure
            try:
                grad_year, test_type, test_date, form = parse_standard_filename(selected_file.name)
                print(f"""Selected file contains grades for:
        Class of {grad_year}'s {test_type} exam taken on {test_date} during their {form} year""")
            except ValueError:
                grad_year = None
                test_type = None
                test_date = None
                form = None
            
            # Parse and Validate CSV
            import_list = csv_to_import_records(selected_file)
        else:
            csv_name = get_filename_from_user(selected_file.name)

            # Parse key fields from standard filenaming structure
            try:
                grad_year, test_type, test_date, form = parse_standard_filename(csv_name)
                print(f"""Selected file contains grades for:
        Class of {grad_year}'s {test_type} exam taken on {test_date} during their {form} year""")
            except ValueError:
                grad_year = None
                test_type = None
                test_date = None
                form = None
            
            # Convert XSLX to CSV
            convert_xlsx_with_openpyxl(selected_file.name, csv_name)

            # Parse and Validate CSV
            selected_file = open(csv_name,mode="r",newline='')
            import_list = csv_to_import_records(selected_file)
            
        # PULL RELEVANT RECORDS AND FIELDS FROM DB
        # Connect to Airtable Table: Students
        b = initialize_airtable()
        students_table = b.table('Students')

        # limit the fields to match on and edit in the students table
        student_import_fields = ['ID','First name','Last name','Grad Class','Zeraki ADM No','KCPE Score']
        
        # limit the records returned by grad year
        try:
            student_records, grad_year= get_students_from_grad_year(student_import_fields,students_table,grad_year)
        except UserQuitOut:
            return False

        # import student details
        if import_type == import_type_options[0]:

            # IMPORT STUDENT DATA
            #import data and print outcome, if user quits out mid-import the summary statement will still show and the students up to that point will have been updated
            total, created, updated = import_students(import_list,student_records,grad_year,students_table,test)
            print(f"Out of {total} total CSV students, {created} new student records were created and {updated} student records were updated.")
            return True

        # import test score details
        elif import_type == import_type_options[1]:
            
            # get test scores table
            grades_table = b.table('Test Scores')
            scores_schema = grades_table.schema()

            # Ask user for test type, test date and which form the student was in when test was taken
            # Check if details already in filename
            if None in (grad_year, test_type, test_date, form):
                # if not, gather details from user and update import list with details
                try:
                    import_list = get_grade_import_details(scores_schema,import_list,grad_year)
                except UserQuitOut:
                    return False
            else:
                # Else if details already in filename, update import list of records with these details
                for rec in import_list:
                    rec.add_test_type(test_type,form,test_date,grad_year)
            
            # import the grades
            print("")
            print(f"Source file: {selected_file.name}")
            print(f"User will be importing {import_list[0].get('test_type')} scores from {import_list[0].get('test_date')} which were taken by the {grad_year} grad year when they were in {import_list[0].get('form')}")
            try:
                import_grades(import_list,student_records,grades_table,test) #could raise UserQuitOut
            except UserQuitOut:
                return False
            return True
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
