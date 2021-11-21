#!/bin/bash 

# remote version
ansible-playbook -i 192.168.1.12, -u pi --ask-pass -vvv rpi_playbook.yaml
