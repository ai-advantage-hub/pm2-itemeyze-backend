# import csv
# from users.models import ManufacturerName 

# def read_csv_and_save_to_model(csv_file_path):
#     with open(csv_file_path, 'r') as file:
#         reader = csv.reader(file)
#         next(reader) 

#         for row in reader:
#             name = row[0]
#             person = ManufacturerName(name=name)
#             person.save()

# if __name__ == "__main__":
#     csv_file_path = "/home/tushar/projects/PM2/pm2-backend/pm2/ManufacturerList 10-2023.xlsx"  # Replace with the actual path to your CSV file
#     read_csv_and_save_to_model(csv_file_path)

import pandas as pd
from users.models import ManufacturerName 

def read_csv_and_save_to_model(csv_file_path):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file_path)

    # Assuming the column containing names is named 'name'
    names = df['name']

    # Iterate over the names and save to the model
    for name in names:
        person = ManufacturerName(name=name)
        person.save()

if __name__ == "__main__":
    csv_file_path = "/home/tushar/projects/PM2/pm2-backend/pm2/ManufacturerList 10-2023.xlsx"  # Replace with the actual path to your CSV file
    read_csv_and_save_to_model(csv_file_path)