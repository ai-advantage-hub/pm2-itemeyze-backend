#!/bin/bash
cd /home/ubuntu/jenkins/workspace/pm2-stage-job/
source venv/bin/activate
cd /home/ubuntu/jenkins/workspace/pm2-stage-job/pm2
python manage.py runserver
