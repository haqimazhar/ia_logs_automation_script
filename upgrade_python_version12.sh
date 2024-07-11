#!/bin/bash

# Update the system
sudo yum update -y

# Install required development tools and libraries
sudo yum groupinstall "Development Tools" -y
sudo yum install gcc openssl-devel bzip2-devel libffi-devel -y

# Download Python 3.12 source code
cd /usr/src
sudo wget https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tgz

# Extract the source code
sudo tar xzf Python-3.12.2.tgz

# Configure the Python build
cd Python-3.12.2
sudo ./configure --enable-optimizations

# Compile Python source code
sudo make -j 8

# Install Python 3.12
sudo make altinstall

# Verify the installation
python3.12 --version
