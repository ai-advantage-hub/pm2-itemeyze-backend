#!/bin/bash

CUSTOM_NAME="pm2"
SCRIPT_PATH="/home/ubuntu/pm2-backend-prod/scripts/pm2-backend-prod.sh"
WORKSPACE="/home/ubuntu/pm2-backend-prod"
sudo chown -R ubuntu:ubuntu /home/ubuntu/pm2-backend-prod

# Navigate to your project directory
cd /home/ubuntu/pm2-backend-prod  # Replace with the actual path to your Django project

# Create a virtual environment inside the project directory
sudo python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

sudo chown -R ubuntu /home/ubuntu/pm2-backend-prod/venv
# Install Python dependencies using pip
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver

# Deactivate the virtual environment when done
deactivate

sudo pm2 start ${SCRIPT_PATH} --name ${CUSTOM_NAME} --silent
sudo chmod 775 -R $WORKSPACE
sudo pm2 status
# Optionally, you can add additional actions or configurations here

exit 0  # Exit with a success code
