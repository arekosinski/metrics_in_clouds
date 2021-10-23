#!/bin/bash

python -m py_compile main.py

mkdir -p ../build
rm -f ../build/cf_iot_data.zip
zip ../build/cf_iot_data.zip requirements.txt main.py