#!/usr/bin/python3
"""
GetPONName.py — Fiberhome RP1000+ (AN5116-06B / AN5516-01)
Descoberta LLD de portas PON via SNMP para o Zabbix.
Também agenda GetONUOnline.py e GetONUSignal.py no cron.

Uso (chamado pelo Zabbix como External Script):
  python3 GetPONName.py <ip> <community> <hostname> <user> <password> <port> [snmp_port]

Sintaxe SNMP confirmada (porta customizada via IP:porta):
  snmpwalk -v 1 -c <community> <IP>:<snmp_port> <OID>

Saída SNMP confirmada:
  iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34078720 = STRING: "PON 1/1"
  (OIDs .1.2 e .1.3 retornam o mesmo valor — alias desnecessário)

Saída: JSON no formato Zabbix LLD
  {"data": [{"{#PONNAME}": "1/1", "{#PONSLOT}": "1", "{#PONPORT}": "1"}]}
"""

import os
import sys
import json
import time


# ---------------------------------------------------------------------------
# OIDs Fiberhome (enterprise 1.3.6.1.4.1.5875)
# ---------------------------------------------------------------------------
OID_PON_PORT_NAME        = "1.3.6.1.4.1.5875.800.3.9.3.4.1.2"   # portName
OID_PON_PORT_DESCRIPTION = "1.3.6.1.4.1.5875.800.3.9.3.4.1.3"   # portDescription
OID_PON_PORT_TYPE        = "1.3.6.1.4.1.5875.800.3.9.3.4.1.1"   # portType (1 = PON)


def parse_pon_index(oid_suffix):
    """
    Converte o índice numérico do OID Fiberhome em slot e pon.
    onuIndex = slot*(2^25) + pon*(2^19) + onuId*(2^8)
    Para PON: onuId = 0
    """
    try:
        idx = int(oid_suffix)
        slot = idx >> 25
        pon  = (idx >> 19) & 0x3F
        return slot, pon
    except Exception:
        return None, None


def snmpwalk(community, ip, oid, snmp_port=161):
    """Executa snmpwalk e retorna as linhas de saída.
    Sintaxe confirmada: IP:porta (ex: 186.209.111.0:55561)
    """
    if int(snmp_port) != 161:
        target = f"{ip}:{snmp_port}"
    else:
        target = ip
    cmd = f'snmpwalk -v 1 -c {community} {target} {oid}'
    return os.popen(cmd).read().splitlines()


def get_pon_list(ip, community, snmp_port=161):
    """
    Descobre as portas PON da OLT Fiberhome via SNMP.
    Retorna lista de dicts com slot, pon, nome e alias.
    """
    pons = {}

    # Busca nomes das portas PON
    for linha in snmpwalk(community, ip, OID_PON_PORT_NAME, snmp_port):
        # Exemplo de linha:
        # SNMPv2-SMI::enterprises.5875.800.3.9.3.4.1.2.<portIndex> = STRING: "PON 1/1"
        if "STRING" not in linha:
            continue
        try:
            oid_part  = linha.split("=")[0].strip()
            val_part  = linha.split("=")[1].strip()
            port_idx  = oid_part.split(".")[-1].strip()
            port_name = val_part.replace("STRING:", "").replace('"', '').strip()

            # Filtra apenas portas PON (nome contém "PON" ou "/" indicando slot/pon)
            if "/" not in port_name:
                continue

            slot, pon = parse_pon_index(port_idx)
            if slot is None:
                continue

            pons[port_idx] = {
                "portIndex": port_idx,
                "slot": str(slot),
                "pon":  str(pon),
                "name": port_name.replace("PON ", "").strip(),  # ex: "1/1"
                "alias": ""
            }
        except Exception:
            continue

    # Busca aliases (descrição) das portas
    for linha in snmpwalk(community, ip, OID_PON_PORT_DESCRIPTION, snmp_port):
        if "STRING" not in linha:
            continue
        try:
            oid_part  = linha.split("=")[0].strip()
            val_part  = linha.split("=")[1].strip()
            port_idx  = oid_part.split(".")[-1].strip()
            alias     = val_part.replace("STRING:", "").replace('"', '').strip()
            if port_idx in pons:
                pons[port_idx]["alias"] = alias
        except Exception:
            continue

    return list(pons.values())


def cron_modify(ip, user, password, port, hostname):
    """
    Adiciona entradas de cron para GetONUOnline.py e GetONUSignal.py
    caso ainda não existam para este hostname.

    Nota: os scripts usam login de dois níveis (User> EN → Admin#).
    As credenciais passadas aqui são usadas em ambos os níveis.
    """
    cron_file = "/etc/cron.d/TemplateOLT"
    try:
        return_cron = os.popen(f"cat {cron_file}").read().splitlines()
    except Exception:
        return_cron = []

    for cron in return_cron:
        if hostname in cron:
            return  # já agendado

    scripts_dir = "/usr/lib/zabbix/externalscripts"

    os.system(f"sudo chmod 777 {cron_file}")
    time.sleep(0.4)

    # GetONUSignal: a cada 2 horas (coleta demorada)
    os.system(
        f'echo "27 */2 * * * zabbix python3 -u {scripts_dir}/GetONUSignal.py'
        f' {ip} {user} {password} {port} {hostname} &" | sudo tee -a {cron_file} > /dev/null'
    )
    time.sleep(0.4)

    # GetONUOnline: a cada 6 minutos
    os.system(
        f'echo "*/6 * * * * zabbix python3 -u {scripts_dir}/GetONUOnline.py'
        f' {ip} {user} {password} {port} {hostname} &" | sudo tee -a {cron_file} > /dev/null'
    )
    time.sleep(0.4)

    os.system(f"sudo chmod 644 {cron_file}")


def main(ip, community, hostname, user, password, port, snmp_port=161):
    pons = get_pon_list(ip, community, snmp_port)

    export = {"data": []}
    for p in pons:
        export["data"].append({
            "{#PONNAME}":  p["name"],    # ex: "1/1"
            "{#PONALIAS}": p["alias"],
            "{#PONSLOT}":  p["slot"],    # ex: "1"
            "{#PONPORT}":  p["pon"],     # ex: "1"
            "{#INDEX}":    p["portIndex"]
        })

    print(json.dumps(export))
    cron_modify(ip, user, password, port, hostname)


if __name__ == "__main__":
    ip        = sys.argv[1]
    community = sys.argv[2]
    hostname  = sys.argv[3]
    user      = sys.argv[4]
    password  = sys.argv[5]
    port      = sys.argv[6]
    snmp_port = sys.argv[7] if len(sys.argv) > 7 else 161  # porta SNMP (padrão: 161)
    main(ip, community, hostname, user, password, port, snmp_port)
