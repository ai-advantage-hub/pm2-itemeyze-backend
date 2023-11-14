#!/usr/bin/bash 

sed -i 's/\[]/\["52.54.174.98"]/' /home/ubuntu/pm2-backend-prod/config/settings.py

python manage.py migrate 
python manage.py makemigrations     
python manage.py collectstatic
sudo service nginx restart