from datetime import datetime, timezone, date, timedelta
import os
import django
from pytz import utc
import sys
sys.path.append('../')
import logging
log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
import datetime
from users.models import User, Project, Files


def delete_projects():
    """cron for deleting projects after 1 year"""

    today = datetime.date.today()
    print(today)
    one_year_ago = today - datetime.timedelta(minutes=5)
    print(one_year_ago)

    try:
        projects_to_delete = Project.objects.filter(is_marked_deleted=True, deleted_at__lte=one_year_ago)
        print("projects to delete", projects_to_delete)
        projects_to_delete.delete()
        logging.info("Project Deleted From Database")
        print("project deleted", projects_to_delete)

    except Exception as e:
        logging.info("HereError", e)
        print("in except")


def delete_files():
    """cron for deleting files after 1 year"""

    today = datetime.date.today()
    print(today)
    one_year_ago = today - datetime.timedelta(days=365)
    print(one_year_ago)

    try:
        files_to_delete = Files.objects.filter(is_marked_deleted=True, deleted_at__lte=one_year_ago)
        print("files to delete", files_to_delete)
        files_to_delete.delete()
        logging.info("File Deleted From Database")
        print("file deleted")

    except Exception as e:
        logging.info("HereError", e)
        print("in exception")

delete_projects()
delete_files()
