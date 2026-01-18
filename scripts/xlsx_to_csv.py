# must move this file to the root directory to run effectively

import openpyxl
import csv
from app import select_file,UserQuitOut,user_selection
import re
from datetime import datetime

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
        test_date = test_dates[year_of_exam][test_type]

        print(f'Original file name is {original_file_name} ')
        new_file_name = f'./to-import/C{grad_year} - {test_type} - {form} - {test_date}.csv'
        print(f'{new_file_name}')
        return new_file_name

def main():
    """Entry point for script to convert files to csv

    Returns:
        bool: True if conversion successful, False otherwise
    """

    # DETERMINE TYPE OF IMPORT
    print("Please select the xlsx file to convert:")
    try:
        # returns file object
        selected_file = select_file()
    except UserQuitOut:
        return False

    csv_name = get_filename_from_user(selected_file.name)

    convert_xlsx_with_openpyxl(selected_file.name, csv_name)

# Example usage:
main()
