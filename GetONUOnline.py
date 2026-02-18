#!/usr/bin/python3
"""
GetONUOnline.py — Fiberhome RP1000+ (AN5116-06B / AN5516-01)
Coleta via Telnet a contagem de ONUs online/offline por porta PON
e envia os dados ao Zabbix via zabbix_sender.

Uso (agendado pelo cron via GetPONName.py):
  python3 GetONUOnline.py <ip> <user> <password> <port> <hostname>

Fluxo de login confirmado:
  1. Banner ASCII → "Login:" → user
  2. "Password:" → senha de usuário → prompt "User>"
  3. "User> EN" → "Password:" → senha admin → prompt "Admin#"

Comandos utilizados:
  Admin# cd service
  Admin\\service# terminal length 0
  Admin# cd onu
  Admin\\onu# show authorization slot all pon all

Formato de saída (confirmado):
  ----- ONU Auth Table, SLOT = 1, PON = 1, ITEM = 9 -----
  Slot Pon Onu OnuType  ST Lic OST PhyId
  1    1   1   HG260    A  1   up  SHLN3c27de63
  1    1   2   HG260    A  1   dn  ZTEGd1ee503c

Encerramento confirmado:
  Admin\\onu# cd ..
  Admin# quit
  User> quit
"""

import sys
import time
import telnetlib
import os
import re


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
TELNET_TIMEOUT = 10
CMD_WAIT       = 0.5
CMD_WAIT_LONG  = 30      # aguarda listagem completa (876+ ONUs)
ZABBIX_SERVER  = "127.0.0.1"


def send_to_zabbix(hostname, key, value):
    """Envia uma métrica ao Zabbix via zabbix_sender."""
    os.system(f'zabbix_sender -z {ZABBIX_SERVER} -s "{hostname}" -k {key} -o {value}')
    time.sleep(0.3)


def get_olt_data(ip, user, password, port, hostname):
    total_provisionado = 0
    total_online       = 0

    # ------------------------------------------------------------------
    # Conexão Telnet
    # ------------------------------------------------------------------
    try:
        tn = telnetlib.Telnet(ip, int(port), TELNET_TIMEOUT)
    except Exception as e:
        print(f"[ERRO] Falha ao conectar via Telnet em {ip}:{port} — {e}", file=sys.stderr)
        return

    # ------------------------------------------------------------------
    # Login nível 1 — usuário comum
    # Banner ASCII aparece antes do "Login:"
    # ------------------------------------------------------------------
    tn.read_until(b"Login:", timeout=15)
    tn.write(user.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

    tn.read_until(b"Password:", timeout=10)
    tn.write(password.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

    # Aguarda prompt "User>"
    tn.read_until(b"User>", timeout=10)

    # ------------------------------------------------------------------
    # Login nível 2 — modo Admin (EN)
    # ------------------------------------------------------------------
    tn.write(b"EN\n")
    time.sleep(CMD_WAIT)

    tn.read_until(b"Password:", timeout=10)
    tn.write(password.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

    # Aguarda prompt "Admin#"
    tn.read_until(b"Admin#", timeout=10)

    # ------------------------------------------------------------------
    # Desabilitar paginação (em modo service)
    # ------------------------------------------------------------------
    tn.write(b"cd service\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin\\service#", timeout=5)

    tn.write(b"terminal length 0\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin\\service#", timeout=5)

    # Volta para Admin#
    tn.write(b"cd ..\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin#", timeout=5)

    # ------------------------------------------------------------------
    # Entra no modo ONU
    # ------------------------------------------------------------------
    tn.write(b"cd onu\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin\\onu#", timeout=5)

    # ------------------------------------------------------------------
    # Coleta todas as ONUs de todos os slots/PONs de uma vez
    # ------------------------------------------------------------------
    tn.write(b"show authorization slot all pon all\n")
    time.sleep(CMD_WAIT_LONG)

    raw = tn.read_until(b"Admin\\onu#", timeout=10).decode("utf-8", errors="ignore")

    # ------------------------------------------------------------------
    # Parse da saída
    # Colunas: Slot Pon Onu OnuType ST Lic OST PhyId ...
    # OST: "up" = online, "dn" = offline
    # ------------------------------------------------------------------
    pon_stats = {}

    for linha in raw.splitlines():
        linha = linha.strip()
        m = re.match(r'^(\d+)\s+(\d+)\s+(\d+)\s+\S+\s+\S+\s+\S+\s+(up|dn)\b', linha)
        if not m:
            continue

        slot = m.group(1)
        pon  = m.group(2)
        ost  = m.group(4)

        key = f"{slot}/{pon}"
        if key not in pon_stats:
            pon_stats[key] = {"online": 0, "total": 0}

        pon_stats[key]["total"] += 1
        if ost == "up":
            pon_stats[key]["online"] += 1

    # ------------------------------------------------------------------
    # Envia métricas por PON ao Zabbix
    # ------------------------------------------------------------------
    for pon_name, stats in pon_stats.items():
        online  = stats["online"]
        offline = stats["total"] - stats["online"]

        send_to_zabbix(hostname, f"OntOnline.[{pon_name}]",  online)
        send_to_zabbix(hostname, f"OntOffline.[{pon_name}]", offline)
        send_to_zabbix(hostname, f"OntProvisioned.[{pon_name}]", stats["total"])

        total_online       += online
        total_provisionado += stats["total"]

    # ------------------------------------------------------------------
    # Envia totais globais
    # ------------------------------------------------------------------
    send_to_zabbix(hostname, "TotalOntProvisioned", total_provisionado)
    send_to_zabbix(hostname, "TotalOntOnline",      total_online)
    send_to_zabbix(hostname, "TotalOntOffline",     total_provisionado - total_online)

    # ------------------------------------------------------------------
    # Encerramento de sessão (confirmado: cd .. → quit → quit)
    # ------------------------------------------------------------------
    tn.write(b"cd ..\n")
    time.sleep(CMD_WAIT)
    tn.write(b"quit\n")
    time.sleep(CMD_WAIT)
    tn.write(b"quit\n")
    time.sleep(CMD_WAIT)
    try:
        tn.close()
    except Exception:
        pass


if __name__ == "__main__":
    ip       = sys.argv[1]
    user     = sys.argv[2]
    password = sys.argv[3]
    port     = sys.argv[4]
    hostname = sys.argv[5]

    get_olt_data(ip, user, password, port, hostname)
