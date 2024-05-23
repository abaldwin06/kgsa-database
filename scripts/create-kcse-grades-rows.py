
def creategrades(year:int,count:int,date:str):
    """Create csv format to import into Test Scores table to document KCSE scores

    Args:
        year (int): year of graduation
        count (int): count of students
        date (str): date of test scores
    """
    print('Date,Form,Type,Subject,Grade,StudentID')
    startid = (year-2000)*100
    for studentID in range(startid,startid+count):
        for subject in ['Overall','ENG','KIS','MAT','BIO','CHE','HIS','CRE','BST']:
            print(f"{date},Form 4,KCSE,{subject},grade,{studentID}")
