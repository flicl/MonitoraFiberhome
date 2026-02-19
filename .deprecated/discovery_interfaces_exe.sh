#!/bin/bash

# Desenvolvido por: Bee Solutions
# Autor: Fernando Almondes
# Data: 11/11/2023

# Use esse script caso tenha problema para executar scripts em python diretamente pelo Zabbix

ip=$1
community=$2

python3 /usr/lib/zabbix/externalscripts/discovery_interfaces.py $ip $community