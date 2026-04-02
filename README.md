# MonitoraFiberhome

Template e scripts para monitoramento de OLT FiberHome no Zabbix.

Compatível com:
- `AN5116-06B`
- `AN5516-01`

## O que o projeto entrega

- descoberta automática de PONs via SNMP
- descoberta de interfaces físicas via IF-MIB
- coleta de status de ONUs via Telnet
- coleta de sinais ópticos via Telnet com `scrapli`
- template pronto para import no Zabbix
- arquitetura pull com External Check + Dependent Items

## Componentes

- [`Template - OLT FiberHome.yaml`](./Template%20-%20OLT%20FiberHome.yaml): template para import no Zabbix
- [`deploy.sh`](./deploy.sh): deploy automático no host Zabbix
- [`RUNBOOK.md`](./RUNBOOK.md): operação detalhada, deploy manual, testes e troubleshooting

## Como funciona

O Zabbix chama wrappers na raiz de `externalscripts`, e esses wrappers carregam os módulos internos em `fiberhome/`.

Resumo do layout no host Zabbix:

```text
/usr/lib/zabbix/externalscripts/
├── fiberhome_olt_status.py
├── fiberhome_olt_signals.py
├── fiberhome_olt_lld.py
├── fiberhome_olt_interfaces.py
└── fiberhome/
    ├── __init__.py
    ├── constants.py
    ├── parsers.py
    ├── scrapli_client.py
    ├── wrapper_utils.py
    ├── fiberhome_olt_status.py
    ├── fiberhome_olt_signals.py
    └── interfaces.py
```

Fluxo:

1. O Zabbix executa um wrapper na raiz de `externalscripts`
2. O wrapper procura `fiberhome/.venv/bin/python`
3. Se a `.venv` existir, ele reexecuta pelo Python dela
4. O módulo interno coleta os dados
5. O script devolve JSON para o template

## Quick Start

### 1. Clonar o projeto

```bash
cd /tmp
git clone https://github.com/flicl/MonitoraFiberhome.git
cd MonitoraFiberhome
```

### 2. Fazer o deploy

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

### 3. Importar o template

Importe no Zabbix:

```text
Template - OLT FiberHome.yaml
```

### 4. Configurar macros no host

| Macro | Exemplo |
|---|---|
| `{$SNMP_COMMUNITY}` | `public` |
| `{$SNMP_PORT}` | `161` |
| `{$OLT_USER}` | `GEPON` |
| `{$OLT_PASSWORD}` | `senha` |
| `{$OLT_PORT}` | `23` |

## Requisitos

### Host Zabbix

- Zabbix Server `6.0+`
- Python `3.10+`
- `python3-venv`
- acesso de saída para instalar dependências via `pip`
- utilitários SNMP

Debian/Ubuntu:

```bash
apt update
apt install -y python3 python3-venv python3-pip snmp
```

RHEL/CentOS/Alma/Rocky:

```bash
yum install -y python3 python3-pip net-snmp
python3 -m ensurepip --upgrade
```

### OLT

- SNMP habilitado
- Telnet habilitado
- usuário e senha válidos

## Operação

O detalhamento operacional ficou no [`RUNBOOK.md`](./RUNBOOK.md):

- deploy automático
- deploy manual
- testes reais
- configuração no Zabbix
- troubleshooting
- referência de CLI FiberHome

## Verificação rápida

Depois do deploy, o teste mais importante é o wrapper real usado pelo Zabbix:

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome_olt_status.py \
  <IP_OLT> <USER> <PASSWORD> <PORTA> | jq .
```

## Estrutura do repositório

```text
.
├── README.md
├── RUNBOOK.md
├── deploy.sh
├── requirements.txt
├── Template - OLT FiberHome.yaml
├── fiberhome_olt_status.py
├── fiberhome_olt_signals.py
├── fiberhome_olt_lld.py
├── fiberhome_olt_interfaces.py
└── fiberhome/
```
