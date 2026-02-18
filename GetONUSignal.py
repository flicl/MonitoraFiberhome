#!/usr/bin/python3
"""
GetONUSignal.py — Fiberhome RP1000+ (AN5116-06B / AN5516-01)
Coleta via Telnet o sinal óptico (RECV_POWER) de todas as ONUs por porta PON,
calcula melhor/pior/média e envia ao Zabbix via zabbix_sender.

Uso (agendado pelo cron via GetPONName.py):
  python3 GetONUSignal.py <ip> <user> <password> <port> <hostname>

Fluxo de login confirmado:
  1. Banner ASCII → "Login:" → user
  2. "Password:" → senha → "User>"
  3. "User> EN" → "Password:" → senha admin → "Admin#"

Comandos utilizados:
  Admin# cd service → terminal length 0 → cd ..
  Admin# cd card
  Admin\\card# show optic_module_para slot X pon Y

Formato de saída confirmado (show optic_module_para slot 1 pon 1):
  ----- PON OPTIC MODULE PAR INFO -----
  NAME          VALUE     UNIT
  TYPE         : 20       (KM)
  TEMPERATURE  : 47.38    ('C)
  VOLTAGE      :  3.23    (V)
  BIAS CURRENT :  7.23    (mA)
  SEND POWER   :  6.11    (Dbm)

  ONU_NO  RECV_POWER , ITEM=9
  1       -27.53  (Dbm)
  2       -21.33  (Dbm)
  ...

Chaves Zabbix enviadas:
  OntBestSinal.[{#PONNAME}]    — Melhor sinal (dBm, positivo)
  OntPoorSinal.[{#PONNAME}]    — Pior sinal (dBm, positivo)
  OntMediaSinal.[{#PONNAME}]   — Mediana do sinal (dBm, positivo)
"""

import sys
import time
import telnetlib
import os
import re
import statistics


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
TELNET_TIMEOUT  = 10
CMD_WAIT        = 0.5
CMD_WAIT_LONG   = 30     # aguarda listagem completa de ONUs
CMD_WAIT_SIGNAL = 5      # aguarda retorno do sinal de uma PON
ZABBIX_SERVER   = "127.0.0.1"


def send_to_zabbix(hostname, key, value):
    """Envia uma métrica ao Zabbix via zabbix_sender."""
    os.system(f'zabbix_sender -z {ZABBIX_SERVER} -s "{hostname}" -k {key} -o {value}')
    time.sleep(0.3)


def get_olt_data(ip, user, password, port, hostname):
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
    # ------------------------------------------------------------------
    tn.read_until(b"Login:", timeout=15)
    tn.write(user.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

    tn.read_until(b"Password:", timeout=10)
    tn.write(password.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

    tn.read_until(b"User>", timeout=10)

    # ------------------------------------------------------------------
    # Login nível 2 — modo Admin (EN)
    # ------------------------------------------------------------------
    tn.write(b"EN\n")
    time.sleep(CMD_WAIT)

    tn.read_until(b"Password:", timeout=10)
    tn.write(password.encode("utf-8") + b"\n")
    time.sleep(CMD_WAIT)

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

    tn.write(b"cd ..\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin#", timeout=5)

    # ------------------------------------------------------------------
    # Passo 1: Descobre pares (slot, pon) existentes via modo ONU
    # ------------------------------------------------------------------
    tn.write(b"cd onu\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin\\onu#", timeout=5)

    tn.write(b"show authorization slot all pon all\n")
    time.sleep(CMD_WAIT_LONG)

    raw_auth = tn.read_until(b"Admin\\onu#", timeout=10).decode("utf-8", errors="ignore")

    # Extrai pares únicos (slot, pon) que têm ao menos uma ONU
    pon_set = set()
    for linha in raw_auth.splitlines():
        linha = linha.strip()
        m = re.match(r'^(\d+)\s+(\d+)\s+\d+\s+\S+\s+\S+\s+\S+\s+(?:up|dn)\b', linha)
        if m:
            pon_set.add((m.group(1), m.group(2)))

    # Volta para Admin#
    tn.write(b"cd ..\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin#", timeout=5)

    # ------------------------------------------------------------------
    # Passo 2: Entra no modo card e coleta sinal por PON
    # Comando: show optic_module_para slot X pon Y
    # Retorna todos os ONUs da PON de uma vez (muito eficiente)
    # ------------------------------------------------------------------
    tn.write(b"cd card\n")
    time.sleep(CMD_WAIT)
    tn.read_until(b"Admin\\card#", timeout=5)

    for slot, pon in sorted(pon_set):
        pon_name = f"{slot}/{pon}"
        cmd = f"show optic_module_para slot {slot} pon {pon}\n"
        tn.write(cmd.encode("utf-8"))
        time.sleep(CMD_WAIT_SIGNAL)

        raw_sig = tn.read_until(b"Admin\\card#", timeout=8).decode("utf-8", errors="ignore")

        # Parse das linhas de ONU:
        # "1       -27.53  (Dbm)"
        # "2       -21.33  (Dbm)"
        sinais = []
        for linha in raw_sig.splitlines():
            linha = linha.strip()
            # Linha começa com número de ONU seguido de valor negativo
            m = re.match(r'^\d+\s+(-\d+\.\d+)\s+\(Dbm\)', linha)
            if m:
                try:
                    sinais.append(float(m.group(1)))
                except ValueError:
                    pass

        if not sinais:
            continue

        # Valores em dBm (negativos); enviamos como positivos ao Zabbix
        melhor = abs(min(sinais, key=abs))   # menor perda = melhor sinal
        pior   = abs(max(sinais, key=abs))   # maior perda = pior sinal
        media  = abs(statistics.median_grouped(sinais))

        send_to_zabbix(hostname, f"OntBestSinal.[{pon_name}]",  melhor)
        send_to_zabbix(hostname, f"OntPoorSinal.[{pon_name}]",  pior)
        send_to_zabbix(hostname, f"OntMediaSinal.[{pon_name}]", media)

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
