#!/bin/bash

# plese keep in mind to login before executing terraform commands
# gcloud auth application-default login

terraform init
if [ "$?" != "0" ]; then
    echo "init error"
    exit
fi

terraform validate
if [ "$?" != "0" ]; then
    echo "validate error"
    exit
fi

terraform plan
if [ "$?" != "0" ]; then
    echo "plan error"
    exit
fi

if [ "$1" == "apply" ]; then
    terraform apply
fi