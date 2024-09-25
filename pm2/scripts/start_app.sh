#!/usr/bin/bash 

sed -i 's/\[]/\["52.54.174.98"]/' /home/ubuntu/pm2-backend-prod/config/settings.py

pwd
source venv/bin/activate

python manage.py migrate 
#python manage.py makemigrations     
python manage.py collectstatic
sudo pm2 restart pm2
sudo service nginx restart