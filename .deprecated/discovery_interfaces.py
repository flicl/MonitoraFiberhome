#!/bin/python3

import subprocess
import re
import json
import sys

# Verifica os argumentos de linha de comando
if len(sys.argv) < 3:
    print("Uso: python discovery_interfaces.py <IP> <community>")
    sys.exit(1)

ip = sys.argv[1]
community = sys.argv[2]

# Executa o comando snmpwalk para obter a Lista 1
cmd_lista1 = f"snmpwalk -On -v2c -c {community} {ip} .1.3.6.1.2.1.31.1.1.1.1 | head -15"
output_lista1 = subprocess.check_output(cmd_lista1, shell=True).decode()

# Executa o comando snmpwalk para obter a Lista 2
cmd_lista2 = f"snmpwalk -On -v2c -c {community} {ip} .1.3.6.1.2.1.2.2.1.3 | head -15"
output_lista2 = subprocess.check_output(cmd_lista2, shell=True).decode()

# Processa a Lista 1
matches1 = re.findall(r'\.1\.3\.6\.1\.2\.1\.31\.1\.1\.1\.1\.(\d+)\s=\sSTRING:\s"([^"]+)"', output_lista1)
lista1 = [{"{#SNMPINDEX}": index, "{#IFNAME}": name} for index, name in matches1[:15]]

# Processa a Lista 2
matches2 = re.findall(r'\.1\.3\.6\.1\.2\.1\.2\.2\.1\.3\.(\d+)\s=\sINTEGER:\s(\d+)', output_lista2)
#matches2 = re.findall(r'.1\.3\.6\.1\.2\.1\.2\.2\.1\.3\.(\d+)\s=\sINTEGER:\s.*\((\d+)\)', output_lista2) # Use caso a saida do walk tenha letras (ethernetCsmacd, ddnX25 e etc)
lista2 = [{"{#SNMPINDEX}": index, "{#IFTYPE}": type} for index, type in matches2[:15]]

# Combina as listas em um único JSON
output = []
for item1, item2 in zip(lista1, lista2):
    output.append({**item1, **item2})

# Converte o JSON em uma string formatada
json_output = json.dumps(output, indent=4)

# Imprime o resultado
print(json_output)