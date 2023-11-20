from users.models import ManufacturerName
import logging
log = logging.getLogger(__name__)
import pandas as pd
from core.response import CustomResponse
from rest_framework import viewsets
import os
import django
import sys
sys.path.append('../')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def readfile():
    try:
        print("tryy")
            # Specify the path to your Excel file
        file_path = "/home/tushar/projects/PM2/pm2-backend/pm2/ManufacturerList 10-2023.xlsx"
            
            # Check if the file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        excel_data = pd.read_excel(file_path, engine='openpyxl', na_filter=False)
        print(excel_data.columns)

        for index, val in excel_data.iterrows():
            print("index", index, val)
            mit, _ = ManufacturerName.objects.get_or_create(name=val.get("MFGName"))
            mit.save()
            print(mit)

    except Exception as e:
        log.info("Error")
        log.info(e)
            # You might want to raise the exception again or handle it accordingly
        raise

    return CustomResponse({"message": "Excel file uploaded Successfully"})

readfile()