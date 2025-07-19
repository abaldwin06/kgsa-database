from app import initialize_airtable

# HOW TO COPY MULTISELECT OPTIONS FROM ONE FIELD TO ANOTHER (CREATING A NEW FIELD)
b = initialize_airtable()
stu = b.table('Students')
surv = b.table('Student Surveys')
stu_schema = stu.schema()
for field in stu_schema.fields:
    if field.name in ['Medical Issues'] and field.type =='multipleSelects':
        try:
            desc = field.description
        except:
            desc = ''
        new_choices = []
        for c in field.options.choices:
            opt = { 'name': c.name, 'color':c.color}
            new_choices.append(opt)
        surv.create_field(name=field.name,type=field.type,description=desc,options={'choices':new_choices})

#TODO - NEED SOME WAY TO KEEP THESE IN SYNC
