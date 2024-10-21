#!/usr/bin/bash 

pwd
cd /home/ubuntu/pm2-backend-prod
pwd
source venv/bin/activate

python manage.py migrate
#python manage.py collectstatic
pm2 restart pm2-backend-prod
sudo service nginx restart