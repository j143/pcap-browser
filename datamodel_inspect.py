from sqlalchemy import create_engine, inspect

engine = create_engine('sqlite:///files.db')
inspector = inspect(engine)

schema = inspector.get_schema_names()[0] # Assuming the schema name is the first one
table_name = 'file' # The name of the table representing the File model
columns = inspector.get_columns(table_name, schema=schema)

print(columns)
