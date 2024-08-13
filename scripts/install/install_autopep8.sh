#!/bin/bash

set -e

sudo apt-get update

# Install pip (if not installed)
echo "Checking if pip is installed..."
if ! command -v pip &> /dev/null
then
    echo "pip is not installed. Installing pip..."
    sudo apt-get install -y python3-pip
fi

# Install autopep8
echo "Installing autopep8..."
pip3 install --user autopep8

# Verify installation
if command -v autopep8 &> /dev/null
then
    echo "autopep8 install success!"
else
    echo "autopep8 installation failed, please check the error message."
fi
