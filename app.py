import os
import csv
from typing import List, Tuple, Optional, TextIO, Literal
from pyairtable import Api, formulas, Table, Base
from pyairtable.api.types import RecordDict, CreateRecordDict
from pyairtable.models.schema import SingleSelectFieldSchema,FieldSchema

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

# CSV Processing Functions
def validate_zeraki_headers(headers:List[str]) -> bool:
    # expected headers
    expected_headers = ['#', 'ADMNO', 'NAME', 'STR', 'KCPE', 'ENG', 'KIS', 'MAT', 'BIO', 'PHY', 'CHE', 'HIS', 'GEO', 'CRE', 'IRE', 'BST', 'SBJ', 'VAP', 'MN MKS', 'GR', 'TT MKS', 'TT PTS', 'MN PTS', 'DEV', 'STR POS', 'OVR POS']
    expected_header_string = ",".join(expected_headers)
    # convert headers to string for print out
    header_string = ','.join(headers)
    if header_string != expected_header_string:
        print("Invalid file to import. Expected first row of headers to be:")
        print("     "+expected_header_string)
        print("But selected file has the following header row:")
        print("     "+header_string)  
        print("Quitting program.")      
        return False
    else:
        print("Successful validation: File headers match expected Zeraki format.")
        #print(header_string)
        return True

def parse_admno(row:List[str],index:int) -> int:
    # Get Zeraki Number
    try:
        zeraki_num = int(row[1])
        #print(f"Row {index}: Processed ADMNO: {zeraki_num}")
        return zeraki_num
    except IndexError:
        print(f"Row {index}: Error identifying Zeraki number in the ADMNO column - no data present.")
        return -1
    except ValueError:
        print(f"Row {index}: Error identifying Zeraki number in the ADMNO column - value '{row[1]}' could not be converted to integer.")
        return -1

def parse_names(row:List[str],index:int) -> Tuple[str,str]:
    # Get Student Name
    try:
        full_name = row[2]
        #print(f"Row {index}: Processed Student: {full_name}")
        names = full_name.split(' ')
        name_count = len(names)
        if name_count < 2 or name_count > 3:
            print(f"Row {index}: Error splitting Student Name into parts: {full_name}, skipping student.")
            return '',''
        else:
            try:
                first_name = names[0]
                last_name = " ".join(names[1:])
                #print(f"Row {index}: First name: {first_name}, Last name: {last_name}.")
                return first_name,last_name
            except IndexError:
                print(f"Row {index}: Error splitting Student Name into parts: {full_name}, skipping student.")
                return '',''
    except IndexError:
        print(f"Row {index}: Error identifying Student Name - no data present.")
        return '',''

def parse_kcpe(row:List[str],index:int)  -> int:
    # Get KCPE Score
    try:
        kcpe_score = int(row[4])
        if kcpe_score <= 0:
            print(f"Row {index}: No KCPE score listed")
            return -1
        print(f"Row {index}: Processed KCPE: {kcpe_score}")
        return kcpe_score
    except IndexError:
        print(f"Row {index}: Error identifying KCPE score - no data present.")
        return -1
    except ValueError:
        print(f"Row {index}: Error identifying KCPE score - value '{row[4]}' could not be converted to integer.")
        return -1

def parse_csv(file:TextIO) -> Optional[List[List[str]]]:
    reader = csv.reader(file)
    headers = next(reader)  # Assume first row is headers
    if validate_zeraki_headers(headers) == False:
        return None
    else:
        # create a 2D list of CSV data
        #   each list item is a row of data, 
        #       each row of data is represented as a list of col values
        data = [row for row in reader]
        return data

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

def import_students(import_data:List[List[str]],student_records:List[RecordDict],grad_year:str,students_table:Table):
    count_total = 0
    count_updated = 0
    count_created = 0

    # Get next available airtable ID for the relevant student records
    at_student_id = get_next_at_student_id(grad_year,student_records)

    # loop through CSV data
    for index,row in enumerate(import_data):
        count_total += 1

        # parse details from CSV
        csv_zeraki_num = parse_admno(row,index)
        csv_first_name, csv_last_name = parse_names(row,index)
        kcpe_score = parse_kcpe(row,index)

        # find if student already exists
        match_type, matching_student = find_matching_student(csv_zeraki_num,csv_first_name,csv_last_name,student_records)

        # do nothing if exact match found    
        if match_type == 'exact':
            print(f"No changes to Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
            continue

        # optionally update student if partial match
        elif match_type == 'adm no':
            db_first_name = matching_student['fields']['First name']
            db_last_name = matching_student['fields']['Last name']
            print(f"Would you like to overwrite {db_first_name} {db_last_name} with {csv_first_name} {csv_last_name} from the CSV file?")
            choice = user_selection(options_list=['Yes','No'],quit_allowed=False)
            if choice == 'Yes':
                updated_student = update_student(matching_student,csv_first_name,csv_last_name,students_table)
                if updated_student == False:
                    print(f"Failed to Update Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
                else:
                    count_updated += 1
                    print(f"Updated Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
            else:
                print(f"No changes to Student: {csv_zeraki_num}, {db_first_name} {db_last_name}.")
        
        # create new student if no match found
        elif match_type == 'no match':
            new_student = import_student(csv_zeraki_num,csv_first_name,csv_last_name,at_student_id,grad_year,students_table)
            if new_student != False:
                count_created += 1
                #increment airtable student id
                at_student_id += 1
                print(f"Imported Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
            else:
                print(f"Failed to Create Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")

        # should never occur
        else:
            print(f"Error encountered trying to match Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name} - No Changes Made.")
    return count_total, count_created, count_updated

def find_matching_student(adm_num:int, f_name:str, l_name:str, students:List[RecordDict]) -> Tuple[Literal['exact', 'adm no', 'no match'],Optional[RecordDict]]:
    match_type = 'no match'
    matched_student = None
    # search airtable data for matching zeraki num, grad class, name
    for student in students:
        if adm_num == student['fields']['Zeraki ADM No']:
            match_type = 'adm no'
            matched_student = student
            
            db_first_name = student['fields']['First name']
            db_last_name = student['fields']['Last name']
            print(f"Student #{adm_num}: {f_name} {l_name} already exists in DB as {db_first_name} {db_last_name}")
            
            if f_name == db_first_name and l_name == db_last_name:
                match_type = 'exact'
            break

    return match_type, matched_student

def update_student(student_record:RecordDict,f_name:str,l_name:str,students_table:Table) -> bool:
    at_record_id = student_record['id']
    updated_fields = {
            'First name': f_name,
            'Last name': l_name,
        }
    try:
        updated_student = students_table.update(at_record_id,updated_fields)
        print(f"Successfully updated record number {updated_student['id']}, Student ID {student_record['fields']['ID']} with name {updated_student['fields']['First name']} {updated_student['fields']['Last name']}")
        return True
    except:
        print(f"Unable to update record number {at_record_id}, Student ID {student_record['fields']['ID']} with name {f_name} {l_name}")
        return False

def import_student(admnum,f_name,l_name,at_id,grad_year,students_table) -> bool:
    student = {
        'ID': at_id,
        'First name': f_name,
        'Last name': l_name,
        'Zeraki ADM No': admnum,
        'Grad Class': grad_year
    }
    try:
        created_student = students_table.create(student)
        print(f"Successfully created Student (record id {created_student['id']}) with Student ID {at_id}, Adm No {admnum} with name {f_name} {l_name} and grad year {grad_year}")
        return True
    except:
        print(f"Unable to create Student with AT ID {at_id}, Adm No {admnum} with name {f_name} {l_name}")
        return False

def get_next_at_student_id(grad_year:str,students:List[RecordDict]) -> int:
    try:
        max_id = max(student['fields']['ID'] for student in students)
        next_id = max_id+1
    except:
        max_id = 0
    if max_id == 0 or max_id == '' or max_id == 'None':
        next_id = (int(grad_year)-2000)*100
    return next_id

# Grades functions
def import_grades():
    # TODO get input from user about grade type
    print("Grade imports not yet supported, quitting program.")
    return False

def main():
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
        csv_data = parse_csv(selected_file)
        if csv_data == None:
            return False
        else:
            
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
                total, created, updated = import_students(csv_data,student_records,grad_year,students_table)
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

if __name__ == "__main__":
    main()
