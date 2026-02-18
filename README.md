# Template OLT Fiberhome RP1000+ para Zabbix
**Modelo confirmado: AN5116-06B / AN5516-01**

Monitoramento de OLTs Fiberhome via Zabbix, com descoberta automática de portas PON (SNMP LLD) e coleta de métricas de ONUs via Telnet.

## Como funciona

```
Zabbix Server
  └─ GetPONName.py (External Check, a cada 1h)
       ├─ SNMP walk → descobre PONs → retorna JSON LLD
       └─ Cron → agenda GetONUOnline.py (*/6 min) e GetONUSignal.py (*/2h)
            ├─ GetONUOnline.py → Telnet → show authorization slot all pon all
            └─ GetONUSignal.py → Telnet → show optic_module_para slot X pon Y
```

## Instalação

### 1. Dependências no servidor Zabbix
```sh
apt update
apt install git snmp python3 zabbix-sender -y
```

### 2. Instalar os scripts
```sh
git clone https://github.com/netoadmredes/template-olt_fiberhome
cp *.py /usr/lib/zabbix/externalscripts/
chmod +x /usr/lib/zabbix/externalscripts/*.py
```

### 3. Criar arquivo de cron (vazio, permissões corretas)
```sh
touch /etc/cron.d/TemplateOLT
chmod 644 /etc/cron.d/TemplateOLT
```

### 4. Permitir que o Zabbix modifique o cron (sudoers)
```sh
visudo
# Adicionar:
zabbix ALL=(ALL) NOPASSWD: /bin/chmod, /bin/echo, /usr/bin/tee
```

---

## Configuração no Zabbix

### 1. Importar o Template
1. No Zabbix, vá em **Configuration > Templates > Import**.
2. Selecione o arquivo `zabbix_template_fiberhome.xml` gerado neste projeto.
3. Marque "Update existing" se necessário e clique em **Import**.
4. Associe o template `Template OLT Fiberhome RP1000+` ao seu host.

### 2. Configurar Macros do Host
Configure os valores das macros no host (ou herde do template):

| Macro | Valor padrão | Descrição |
|---|---|---|
| `{$SNMP_COMMUNITY}` | `public` | Community SNMP |
| `{$SNMP_PORT}` | `161` | Porta SNMP (use porta customizada se necessário) |
| `{$OLT_USER}` | `GEPON` | Usuário Telnet |
| `{$OLT_PASSWORD}` | `GEPON` | Senha Telnet (usada nos dois níveis de login) |
| `{$OLT_PORT}` | `23` | Porta Telnet |

### Item de descoberta (LLD)

| Campo | Valor |
|---|---|
| Nome | `Descoberta de PONs` |
| Tipo | `External check` |
| Chave | `GetPONName.py[{HOST.CONN},{$SNMP_COMMUNITY},{HOST.HOST},{$OLT_USER},{$OLT_PASSWORD},{$OLT_PORT},{$SNMP_PORT}]` |
| Intervalo | `1h` |

### Protótipos de itens (criados automaticamente pelo LLD)

| Chave | Descrição |
|---|---|
| `OntOnline.[{#PONNAME}]` | ONUs online na PON (ex: `1/1`) |
| `OntOffline.[{#PONNAME}]` | ONUs offline na PON |
| `OntBestSinal.[{#PONNAME}]` | Melhor sinal óptico (dBm positivo) |
| `OntPoorSinal.[{#PONNAME}]` | Pior sinal óptico (dBm positivo) |
| `OntMediaSinal.[{#PONNAME}]` | Mediana do sinal óptico |

### Itens globais (Zabbix Trapper)

| Chave | Descrição |
|---|---|
| `TotalOntProvisioned` | Total de ONUs provisionadas na OLT |
| `TotalOntOnline` | Total de ONUs online |
| `TotalOntOffline` | Total de ONUs offline |

---

## Comandos CLI confirmados (Fiberhome AN5116-06B / AN5516-01)

### Login (dois níveis)
```
[Banner ASCII]
Login: GEPON
Password: ****
User> EN
Password: ****
Admin#
```

### Desabilitar paginação
```
Admin# cd service
Admin\service# terminal length 0
Admin\service# cd ..
Admin#
```

### Listar ONUs online/offline
```
Admin# cd onu
Admin\onu# show authorization slot all pon all
```
**Saída:**
```
----- ONU Auth Table, Total ITEM = 876 -----

----- ONU Auth Table, SLOT = 1, PON = 1, ITEM = 9 -----
Slot Pon Onu OnuType        ST Lic OST PhyId
1    1   1   HG260          A  1   up  SHLN3c27de63
1    1   2   HG260          A  1   dn  ZTEGd1ee503c
```
- **OST = `up`** → online | **OST = `dn`** → offline

### Sinal óptico por PON (todos os ONUs de uma vez)
```
Admin# cd card
Admin\card# show optic_module_para slot 1 pon 1
```
**Saída:**
```
----- PON OPTIC MODULE PAR INFO -----
NAME          VALUE     UNIT
SEND POWER   :  6.11    (Dbm)

ONU_NO  RECV_POWER , ITEM=9
1       -27.53  (Dbm)
2       -21.33  (Dbm)
3       -23.17  (Dbm)
```

### Encerramento de sessão
```
Admin\<modo># cd ..
Admin# quit
User> quit
```

### SNMP — descoberta de PONs
```sh
# Porta padrão (161):
snmpwalk -v 1 -c <community> <IP> 1.3.6.1.4.1.5875.800.3.9.3.4.1.2

# Porta customizada (ex: 55561):
snmpwalk -v 1 -c <community> <IP>:55561 1.3.6.1.4.1.5875.800.3.9.3.4.1.2
```
**Saída:**
```
iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34078720 = STRING: "PON 1/1"
iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34603008 = STRING: "PON 1/2"
...
iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.138412032 = STRING: "PON 4/8"
```

---

## Observações

- A senha é a mesma para o login de usuário (`User>`) e para o modo admin (`EN`). Se forem diferentes no seu ambiente, ajuste o script para aceitar dois parâmetros de senha separados.
- O `GetONUSignal.py` é eficiente: usa `show optic_module_para slot X pon Y` que retorna todos os ONUs da PON de uma vez (sem loop por ONU).
- O SNMP usa versão 1 (`-v 1`) conforme confirmado. Se precisar de v2c, altere `snmpwalk -v 1` para `snmpwalk -v 2c` nos scripts.
