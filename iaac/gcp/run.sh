#!/bin/bash

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