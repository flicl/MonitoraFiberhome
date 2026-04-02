#!/usr/bin/python3
"""
GetPONName.py — Fiberhome RP1000+ (AN5116-06B / AN5516-01)
Descoberta LLD de portas PON via SNMP para o Zabbix.

Uso (chamado pelo Zabbix como External Script):
  python3 GetPONName.py <ip> <community> <hostname> <user> <password> <port> [snmp_port]

Sintaxe SNMP confirmada (porta customizada via IP:porta):
  snmpwalk -v 1 -c <community> <IP>:<snmp_port> <OID>

Saída SNMP confirmada:
  iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34078720 = STRING: "PON 1/1"
  (OIDs .1.2 e .1.3 retornam o mesmo valor — alias desnecessário)

Saída: JSON no formato Zabbix LLD
  {"data": [{"{#PONNAME}": "1/1", "{#PONSLOT}": "1", "{#PONPORT}": "1"}]}

Nota: A partir da v2.0, este script NÃO configura mais cron.
      O monitoramento usa Zabbix Dependent Items (pull model).
"""

import os
import sys
import json


# ---------------------------------------------------------------------------
# OIDs Fiberhome (enterprise 1.3.6.1.4.1.5875)
# ---------------------------------------------------------------------------
OID_PON_PORT_NAME = "1.3.6.1.4.1.5875.800.3.9.3.4.1.2"
OID_PON_PORT_DESCRIPTION = "1.3.6.1.4.1.5875.800.3.9.3.4.1.3"


def parse_pon_index(oid_suffix: str) -> tuple[int | None, int | None]:
    """
    Converte o índice numérico do OID Fiberhome em slot e pon.
    onuIndex = slot*(2^25) + pon*(2^19) + onuId*(2^8)
    Para PON: onuId = 0
    """
    try:
        idx = int(oid_suffix)
        slot = idx >> 25
        pon = (idx >> 19) & 0x3F
        return slot, pon
    except Exception:
        return None, None


def snmpwalk(community: str, ip: str, oid: str, snmp_port: int = 161) -> list[str]:
    """Executa snmpwalk e retorna as linhas de saída."""
    target = f"{ip}:{snmp_port}" if snmp_port != 161 else ip
    cmd = f'snmpwalk -v 1 -c {community} {target} {oid}'
    return os.popen(cmd).read().splitlines()


def get_pon_list(ip: str, community: str, snmp_port: int = 161) -> list[dict]:
    """
    Descobre as portas PON da OLT Fiberhome via SNMP.
    Retorna lista de dicts com slot, pon, nome e alias.
    """
    pons: dict[str, dict] = {}

    # Busca nomes das portas PON
    for linha in snmpwalk(community, ip, OID_PON_PORT_NAME, snmp_port):
        if "STRING" not in linha:
            continue
        try:
            oid_part = linha.split("=")[0].strip()
            val_part = linha.split("=")[1].strip()
            port_idx = oid_part.split(".")[-1].strip()
            port_name = val_part.replace("STRING:", "").replace('"', '').strip()

            # Filtra apenas portas PON (nome contém "/" indicando slot/pon)
            if "/" not in port_name:
                continue

            slot, pon = parse_pon_index(port_idx)
            if slot is None:
                continue

            pons[port_idx] = {
                "portIndex": port_idx,
                "slot": str(slot),
                "pon": str(pon),
                "name": port_name.replace("PON ", "").strip(),
                "alias": ""
            }
        except Exception:
            continue

    # Busca aliases (descrição) das portas
    for linha in snmpwalk(community, ip, OID_PON_PORT_DESCRIPTION, snmp_port):
        if "STRING" not in linha:
            continue
        try:
            oid_part = linha.split("=")[0].strip()
            val_part = linha.split("=")[1].strip()
            port_idx = oid_part.split(".")[-1].strip()
            alias = val_part.replace("STRING:", "").replace('"', '').strip()
            if port_idx in pons:
                pons[port_idx]["alias"] = alias
        except Exception:
            continue

    return list(pons.values())


def main(
    ip: str,
    community: str,
    hostname: str,
    user: str,
    password: str,
    port: str,
    snmp_port: int = 161
) -> None:
    """
    Executa LLD e retorna JSON para Zabbix.

    Nota: user, password, port são ignorados (mantidos para compatibilidade)
    """
    pons = get_pon_list(ip, community, snmp_port)

    export = {"data": []}
    for p in pons:
        export["data"].append({
            "{#PONNAME}": p["name"],
            "{#PONALIAS}": p["alias"],
            "{#PONSLOT}": p["slot"],
            "{#PONPORT}": p["pon"],
            "{#INDEX}": p["portIndex"]
        })

    print(json.dumps(export))


if __name__ == "__main__":
    ip = sys.argv[1]
    community = sys.argv[2]
    hostname = sys.argv[3]
    user = sys.argv[4]
    password = sys.argv[5]
    port = sys.argv[6]
    snmp_port = int(sys.argv[7]) if len(sys.argv) > 7 else 161

    main(ip, community, hostname, user, password, port, snmp_port)
