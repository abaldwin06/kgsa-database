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
