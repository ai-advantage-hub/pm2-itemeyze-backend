#!/bin/bash

# Define the source and destination paths
local_py_source="/opt/env/local.py"  # Replace with the actual path to local.py on your server
django_project_dir="/home/ubuntu/pm2-backend-prod"  # Replace with the actual path to your Django project

# Check if the local.py source file exists
if [ -f "$local_py_source" ]; then
  # Copy the local.py file to the Django project directory
  cp "$local_py_source" "$django_project_dir/config/local.py"  # Assuming your Django project's settings are in a 'config' directory
  echo "local.py copied successfully."
else
  echo "Error: local.py file not found at $local_py_source."
  exit 1  # Exit with an error code
fi

# Optionally, you can add additional actions or configurations here

exit 0  # Exit with a success code
