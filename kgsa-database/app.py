import os
import csv
from pyairtable import Api, Base, Table

def initialize_airtable():
    """Find access key, connect to airtable, and retrieve the database object

    Returns:
        Base object: the KGSA database object
    """
    # ============ Access Key Filename and Location ============
    access_key_filename = '.abaldwin-kgsa-airtable-token.txt'
    access_key_path = os.pardir

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
    """Select the CSV file to import into Airtable from the files in the 'to-import' folder of the parent folder

    Returns:
        string: file contents of user selected file, or 'quit' if user wants to exit program
    """
    
    folder_name = 'to-import'
    
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
        print("Successful validation: File headers match expected Zeraki format:")
        print(header_string)
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

def import_data(file,import_type):
    reader = csv.reader(file)
    headers = next(reader)  # Assume first row is headers
    if validate_zeraki_headers(headers) == False:
        return False
    else:
        # initialize connection to Airtable 
        b = initialize_airtable()
        student_table = b.table('Students')

        #Field IDs: 
        # fldFkXG0Z175zUmey for 'ID'
        # fldiWUkxxMkjN2gub First name
        # fldmuYfJMvj3U3K2I Last name
        # fldesqKtW9GFOgffL Grad Class
        # fldV1ZJpma7J47F8O Zeraki ADM No

        # get input from user about grad class (pick from allowed values)
        # TODO

        # get list of students for grad year with Zeraki numbers
        # TODO

        # REMOVE THIS
        return True
        # create a 2D list of CSV data
        #   each list item is a row of data, 
        #       each row of data is represented as a list of col values
        data = [row for row in reader]

        # loop through CSV data
        for index,row in enumerate(data):
            zeraki_num = parse_admno(row,index)
            first_name, last_name = parse_names(row,index)
            if import_type == 'students':
                # search airtable data for matching zeraki num, grad class, name
                # TODO
                # if exact match found, some kind of output that we'll skip this patient
                # TODO
                # if partial match found (name is fuzzy match), get user input of "would you like to update this student's name?"
                # TODO
                # if match not found - create object w/ name, zeraki num, grad class
                # TODO
                # create airtable id num (need function from ther script)
                # TODO
                pass
            elif import_type == 'grades':
                # TODO get input from user about grade type
                print("Grade imports not yet supported, quitting program.")
                return False
            else:
                print(f"Import type {import_type} not supported, quitting program.")
                return False
            print(f"Row {index}: Processed Student: {zeraki_num}, {first_name} {last_name}.")



def main():
    """Main program that calls user input functions and import functions

    Returns:
        bool: True if import successful, False otherwise
    """
    print("Welcome to the KGSA Airtable import tool.")
    
    import_type = select_import_type()
    if import_type == 'quit':
        return False
    file = select_file()
    if select_file == 'quit':
        return False
    elif import_type in ['students','grades']:
        outcome = import_data(file,import_type)
        return outcome
    else:
        print("Invalid import type, quitting program.")
        return False



if __name__ == "__main__":
    main()
