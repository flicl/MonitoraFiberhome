# RUNBOOK

Runbook operacional do `MonitoraFiberhome`.

## Deploy Automático

O `deploy.sh`:
- cria `/usr/lib/zabbix/externalscripts/fiberhome/`
- copia wrappers e módulos
- cria `.venv` em `fiberhome/.venv`
- instala dependências do `requirements.txt`
- ajusta permissões para `zabbix:zabbix`
- valida sintaxe dos scripts

Execução:

```bash
sudo ./deploy.sh
```

Com backup:

```bash
sudo ./deploy.sh --backup
```

Verificação rápida:

```bash
ls -la /usr/lib/zabbix/externalscripts/
ls -la /usr/lib/zabbix/externalscripts/fiberhome/
ls -la /usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python
```

## Deploy Manual

### 1. Criar diretórios

```bash
sudo mkdir -p /usr/lib/zabbix/externalscripts/fiberhome
```

### 2. Copiar wrappers para a raiz

```bash
sudo cp fiberhome_olt_status.py /usr/lib/zabbix/externalscripts/
sudo cp fiberhome_olt_signals.py /usr/lib/zabbix/externalscripts/
sudo cp fiberhome_olt_lld.py /usr/lib/zabbix/externalscripts/
```

### 3. Copiar módulos para `fiberhome/`

```bash
sudo cp fiberhome/*.py /usr/lib/zabbix/externalscripts/fiberhome/
```

### 4. Criar a `.venv`

```bash
sudo python3 -m venv /usr/lib/zabbix/externalscripts/fiberhome/.venv
sudo /usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python -m pip install -U pip
sudo /usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python -m pip install -r "$(pwd)/requirements.txt"
```

### 5. Ajustar permissões

```bash
sudo chmod +x /usr/lib/zabbix/externalscripts/fiberhome_olt_status.py
sudo chmod +x /usr/lib/zabbix/externalscripts/fiberhome_olt_signals.py
sudo chmod +x /usr/lib/zabbix/externalscripts/fiberhome_olt_lld.py
sudo chown -R zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome_olt_status.py
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome_olt_signals.py
sudo chown zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome_olt_lld.py
```

### 6. Validar instalação

```bash
sudo /usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python -m py_compile \
  /usr/lib/zabbix/externalscripts/fiberhome/scrapli_client.py \
  /usr/lib/zabbix/externalscripts/fiberhome/wrapper_utils.py \
  /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_status.py \
  /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_signals.py \
  /usr/lib/zabbix/externalscripts/fiberhome_olt_status.py \
  /usr/lib/zabbix/externalscripts/fiberhome_olt_signals.py
```

## Testes Reais

### Teste de SNMP

```bash
snmpwalk -v 1 -c <COMMUNITY> <IP_OLT>:<SNMP_PORT> 1.3.6.1.4.1.5875.800.3.9.3.4.1.2
```

### Teste do wrapper de status

Esse é o teste mais importante, porque é o mesmo caminho usado pelo Zabbix:

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome_olt_status.py \
  <IP_OLT> <USER> <PASSWORD> <PORTA> | jq .
```

### Teste do wrapper de sinais

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome_olt_signals.py \
  <IP_OLT> <USER> <PASSWORD> <PORTA> | jq .
```

### Teste do LLD de PON

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome_olt_lld.py \
  <IP_OLT> <SNMP_COMMUNITY> <HOSTNAME> <USER> <PASSWORD> <TELNET_PORT> <SNMP_PORT> | jq .
```

### Teste do Python da `.venv`

```bash
/usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python -c "import scrapli; print(scrapli.__version__)"
```

## Configuração no Zabbix

### Importar template

Importe:

```text
Template - OLT FiberHome.yaml
```

### Linkar ao host

No host da OLT:
- configure `Host connection` com o IP da OLT
- linke o template `TriplePlay - OLT FiberHome`

### Macros obrigatórias

| Macro | Uso |
|---|---|
| `{$SNMP_COMMUNITY}` | comunidade SNMP |
| `{$SNMP_PORT}` | porta SNMP |
| `{$OLT_USER}` | usuário Telnet |
| `{$OLT_PASSWORD}` | senha Telnet |
| `{$OLT_PORT}` | porta Telnet |

Nenhuma macro extra foi criada para o `scrapli`.

## Troubleshooting

### `No module named scrapli`

Verifique:

```bash
ls -la /usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python
/usr/lib/zabbix/externalscripts/fiberhome/.venv/bin/python -m pip show scrapli
```

### Timeout ou erro de conexão no Telnet

```bash
telnet <IP_OLT> 23
```

Se o login manual falhar, o script também vai falhar.

### Wrapper funciona local, mas falha no Zabbix

```bash
ls -la /usr/lib/zabbix/externalscripts/
ls -la /usr/lib/zabbix/externalscripts/fiberhome/
sudo chown -R zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome
```

### Logs

```bash
tail -f /var/log/zabbix/zabbix_server.log | grep -i fiberhome
journalctl -u zabbix-server -f
```

## Referência

### Layout no host Zabbix

```text
/usr/lib/zabbix/externalscripts/
├── fiberhome_olt_status.py
├── fiberhome_olt_signals.py
├── fiberhome_olt_lld.py
└── fiberhome/
    ├── __init__.py
    ├── constants.py
    ├── parsers.py
    ├── scrapli_client.py
    ├── wrapper_utils.py
    ├── fiberhome_olt_status.py
    ├── fiberhome_olt_signals.py
    └── fiberhome_olt_signals.py
```

### Principais arquivos

- `fiberhome_olt_status.py`: wrapper do master item de status
- `fiberhome_olt_signals.py`: wrapper do master item de sinais
- `fiberhome_olt_lld.py`: descoberta de PONs via SNMP
- `fiberhome/scrapli_client.py`: cliente Telnet assíncrono com `scrapli`

### CLI da FiberHome

Login em dois níveis:

```text
Login: <USER>
Password: <PASSWORD>
User> EN
Password: <PASSWORD>
Admin#
```

Paginação:

```text
Admin# cd service
Admin\service# terminal length 0
Admin\service# cd ..
```

Comandos principais:

```text
Admin# cd onu
Admin\onu# show authorization slot all pon all

Admin# cd card
Admin\card# show optic_module_para slot <SLOT> pon <PON>
```
