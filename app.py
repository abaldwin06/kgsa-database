import os
import csv
from pyairtable import Api, formulas
from pyairtable.models.schema import SingleSelectFieldSchema

# User Input Functions
def user_selection(options_list:list,quit_allowed:bool=True):
    for idx, option in enumerate(options_list,start=1):
        print(f"{idx}: {option}")
    
    # Get user input
    while True:
        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice == 'q' and quit_allowed == True:
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

def list_files(directory):
    """List all files in the given directory and return a list of file names.

    Args:
        directory (string): pull path to the 'to-import' folder, expected in the parent directory of th eprogram

    Returns:
        list of strings: list of filepaths to files in the 'to-import' folder
    """
    files = os.listdir(directory)
    files = [f for f in files if os.path.isfile(os.path.join(directory, f))]
    return files

def select_file():
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
    # Full path of the selected file
    selected_file_path = os.path.join(folder_name, selected_file_name)
    selected_file = open(selected_file_path,mode="r",newline='')
    return selected_file

    for idx, file in enumerate(files,start=1):
        print(f"{idx}: {file}")
    
    # Get user input
    while True:
        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice == 'q':
            print("Quitting the program.")
            return 'quit'
        else:
            try:
                user_choice_int = int(user_choice)
                if user_choice_int <= 0 or user_choice_int > len(files):
                    print("Invalid number entered. Please enter a valid number.")
                else:
                    selected_file = files[user_choice_int-1]
                    print(f"You have selected: {selected_file}")

                    # Full path of the selected file
                    selected_file_path = os.path.join(folder_name, selected_file)
                    file = open(selected_file_path,mode="r",newline='')
                    return file
            except ValueError as e:
                print("Please enter a valid number.")

def select_import_type():
    """Selects what kind of import the user would like to do, offering the option to quit out

    Returns:
        string: 'grades', 'students', or 'quit' based on user input
    """
    print("Please choose an option:")
    print("1: Import students from Zeraki")
    print("2: Import grades from Zeraki")

    while True:
        user_choice = input("Enter the number of your choice: ").strip().lower()
        if user_choice == 'q':
            print("Quitting the program.")
            return 'quit'
        else:
            try:
                user_choice_int = int(user_choice)
                if user_choice_int == 1:
                    print("Import of students selected.")
                    return 'students'
                elif user_choice_int == 2:
                    print("Import of grades selected.")
                    return 'grades'
                else:
                    print("Invalid choice. Please enter '1', '2', or 'q'")
            except ValueError:
                print("Invalid input. Please enter '1', '2', or 'q'")

# CSV Processing Functions
def validate_zeraki_headers(headers):
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

def parse_admno(row,index):
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

def parse_names(row, index):
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

def parse_csv(file):
    reader = csv.reader(file)
    headers = next(reader)  # Assume first row is headers
    if validate_zeraki_headers(headers) == False:
        return False
    else:
        # create a 2D list of CSV data
        #   each list item is a row of data, 
        #       each row of data is represented as a list of col values
        data = [row for row in reader]
        return data

# Airtable functions
def initialize_airtable():
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

def get_field_options(field):
    allowed_values = field.options.choices
    return_list = []
    for val in allowed_values:
        return_list.append(val.name)
    return return_list

# Student functions
def get_students_from_grad_year(fields):
    b = initialize_airtable()
    students_table = b.table('Students')
    grad_yr_field = students_table.schema().field('Grad Class')
    grad_yr_options = get_field_options(grad_yr_field)
    print('Please select the graduating class year for the students you are importing:')
    selected_grad_yr = user_selection(grad_yr_options)
    if selected_grad_yr == 'quit':
        return False, False
    else:
        formula = formulas.match({'Grad Class': selected_grad_yr})
        records = students_table.all(fields=fields, formula=formula)
        return records, selected_grad_yr

def find_matching_student(adm_num, f_name, l_name, students):
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

def import_students(import_data,student_records,grad_year:int):
    count_total = 0
    count_updated = 0
    count_created = 0

    # Get max airtable ID for the relevant student records

    # loop through CSV data
    for index,row in enumerate(import_data):
        count_total += 1

        # parse details from CSV
        csv_zeraki_num = parse_admno(row,index)
        csv_first_name, csv_last_name = parse_names(row,index)

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
                updated_student = update_student(matching_student,csv_first_name,csv_last_name)
                if updated_student == False:
                    print(f"Failed to Update Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
                else:
                    count_updated += 1
                    print(f"Updated Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
            else:
                print(f"No changes to Student: {csv_zeraki_num}, {db_first_name} {db_last_name}.")
        
        # create new student if no match found
        elif match_type == 'no match':
            at_student_id = create_airtable_student_id(grad_year,student_records)
            new_student = import_student(csv_zeraki_num,csv_first_name,csv_last_name,at_student_id,grad_year)
            if new_student != False:
                count_created += 1
                print(f"Imported Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")
            else:
                print(f"Failed to Create Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name}.")

        # should never occur
        else:
            print(f"Error encountered trying to match Student: {csv_zeraki_num}, {csv_first_name} {csv_last_name} - No Changes Made.")
    return count_total, count_created, count_updated

def update_student(student_record,f_name,l_name):
    print(f"Would UPDATE student in class of {student_record['fields']['Grad Class']} with AT ID {student_record['fields']['ID']}, Adm No {student_record['fields']['Zeraki ADM No']} with name {f_name} {l_name}")
    # if partial match found (name is fuzzy match), get user input of "would you like to update this student's name?"
    # TODO
    return True

def import_student(admnum,f_name,l_name,at_id,grad_year):
    print(f"Would CREATE new student in class of {grad_year} with AT ID {at_id}, Adm No {admnum} and name {f_name} {l_name}")
    # if match not found - create object w/ name, zeraki num, grad class
    # TODO
    return True

def create_airtable_student_id(grad_year,students):
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
    
    import_type = select_import_type()
    if import_type == 'quit':
        return False
    elif import_type in ['students','grades']:
        # Select CSV to import
        selected_file = select_file()
        if selected_file == 'quit':
            return False

        # Parse and Validate CSV
        csv_data = parse_csv(selected_file)
        if csv_data == False:
            return False
        else:
            if import_type == 'students':
                # limit the fields returned
                student_import_fields = ['ID','First name','Last name','Grad Class','Zeraki ADM No']
                # limit the records returned by grad year
                student_records, grad_year = get_students_from_grad_year(student_import_fields)
                if student_records == False:
                    return False

                #import data and print outcome
                total, created, updated = import_students(csv_data,student_records,grad_year)
                print(f"Out of {total} total CSV students, {created} new student records were created and {updated} student records were updated.")
                return True

            elif import_type == 'grades':
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
