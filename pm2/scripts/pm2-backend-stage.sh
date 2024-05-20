#!/bin/bash
cd /home/ubuntu/jenkins/workspace/pm2-stage-backend/
source venv/bin/activate
cd /home/ubuntu/jenkins/workspace/pm2-stage-backend/pm2
python manage.py runserver
