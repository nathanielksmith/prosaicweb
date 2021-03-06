#!/bin/bash
# This file is 90% documentation; but if run on a clean system, it should set up
# everything needed for prosaicweb.

set -x

echo "installing packages..."
sudo apt-get update
sudo apt-get -y install \
     python3 \
     python3-setuptools \
     postgresql \
     build-essential \
     postgresql-server-dev-9.5 \
     python3-dev \
     python3-venv \
     libffi-dev

echo "starting postgresql"
sudo service postgresql start

echo "configuring postgresql"
sudo su postgres -c "psql -c \"create user prosaic with password 'prosaic'\""
sudo su postgres -c "createdb prosaic -O prosaic"

echo "creating venv"
mkdir ~/venv
python3 -mvenv ~/venv/prosaicweb
source ~/venv/prosaicweb/bin/activate

echo "installing prosaicweb"
pip install -e .

echo "initializing db tables"
prosaicweb dbinit
