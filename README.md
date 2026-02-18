# 📡 Template OLT Fiberhome para Zabbix

**Modelos compatíveis:** AN5116-06B / AN5516-01

Monitoramento completo de OLTs Fiberhome via Zabbix com:
- 📊 Descoberta automática de portas PON (SNMP LLD)
- 📈 Coleta de métricas de ONUs via Telnet
- 🔄 Arquitetura Pull (Zabbix chama os scripts)
- ⚡ Async/await para I/O não-bloqueante

---

## 📋 Índice

- [Arquitetura](#-arquitetura)
- [Requisitos](#-requisitos)
- [Tutorial de Instalação](#-tutorial-de-instalação)
- [Configuração no Zabbix](#-configuração-no-zabbix)
- [Testando os Scripts](#-testando-os-scripts)
- [Métricas Coletadas](#-métricas-coletadas)
- [Migração da Versão Antiga](#-migração-da-versão-antiga)
- [Troubleshooting](#-troubleshooting)

---

## 🏗️ Arquitetura

```mermaid
flowchart TB
    subgraph ZABBIX["ZABBIX SERVER"]
        subgraph LLD["Descoberta SNMP"]
            LLD_SCRIPT["GetPONName.py<br/>(SNMP LLD)<br/>Interval: 1h"]
        end

        subgraph STATUS["Status ONUs"]
            STATUS_MASTER["fiberhome_olt_status.py<br/>(Master Item - JSON)<br/>Interval: 6min"]
            STATUS_DEPS["Dependent Items:<br/>• OntOnline.[PON]<br/>• OntOffline.[PON]<br/>• OntProvisioned.[PON]<br/>• TotalOntOnline<br/>• TotalOntOffline<br/>• TotalOntProvisioned"]
        end

        subgraph SIGNALS["Sinais Ópticos"]
            SIGNALS_MASTER["fiberhome_olt_signals.py<br/>(Master Item - JSON)<br/>Interval: 2h"]
            SIGNALS_DEPS["Dependent Items:<br/>• OntBestSinal.[PON]<br/>• OntPoorSinal.[PON]<br/>• OntMediaSinal.[PON]"]
        end
    end

    subgraph OLT["OLT FIBERHOME"]
        OLT_TELNET["Telnet<br/>Porta 23"]
        OLT_SNMP["SNMP<br/>Porta 161"]
    end

    LLD_SCRIPT -->|"Descobre<br/>{#PONNAME}<br/>{#PONSLOT}<br/>{#PONPORT}"| STATUS_DEPS
    STATUS_MASTER --> STATUS_DEPS
    SIGNALS_MASTER --> SIGNALS_DEPS

    LLD_SCRIPT -->|"SNMP"| OLT_SNMP
    STATUS_MASTER -->|"Telnet"| OLT_TELNET
    SIGNALS_MASTER -->|"Telnet"| OLT_TELNET
```

### ✅ Benefícios

| Antes (v1.0) | Depois (v2.0) |
|--------------|---------------|
| zabbix_sender (push) | Pull via External Check |
| Cron dinâmico por host | Zero cron |
| telnetlib (deprecated Python 3.13) | asyncio nativo |
| Múltiplas conexões por coleta | Uma conexão por coleta |
| 0.3s sleep por envio | I/O não-bloqueante |

---

## 💻 Requisitos

### Servidor Zabbix

| Requisito | Versão Mínima |
|-----------|---------------|
| Zabbix Server | 6.0+ |
| Python | 3.10+ |
| Sistema | Linux (systemd) |

### Pacotes necessários

```bash
# Debian/Ubuntu
apt update
apt install -y python3 snmp zabbix-sender

# RHEL/CentOS
yum install -y python39 net-snmp zabbix-sender
```

### OLT Fiberhome

- SNMP v1/v2c habilitado
- Acesso Telnet na porta 23
- Usuário/senha de autenticação

---

## 📦 Tutorial de Instalação

### Passo 1: Clonar o repositório

```bash
cd /tmp
git clone https://github.com/flicl/MonitoraFiberhome.git
cd MonitoraFiberhome
```

### Passo 2: Executar o script de deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

**O que o script faz:**
- ✅ Verifica Python >= 3.10
- ✅ Cria diretório `/usr/lib/zabbix/externalscripts/fiberhome/`
- ✅ Copia todos os scripts
- ✅ Configura permissões (zabbix:zabbix)
- ✅ Faz backup dos scripts legados (se existirem)

**Saída esperada:**
```
[INFO] Checking Python version...
[INFO] Python version: 3.11.2
[INFO] Python version OK (no external dependencies required)
[INFO] Creating directory structure...
[INFO] Deploying scripts...
[INFO] Scripts deployed successfully
[INFO] Testing script syntax...
[INFO] Syntax check passed
```

### Passo 3: Verificar instalação

```bash
ls -la /usr/lib/zabbix/externalscripts/fiberhome/
```

**Deve mostrar:**
```
drwxr-xr-x  zabbix zabbix  4096 ./
-rw-r--r--  1 zabbix zabbix   403 __init__.py
-rw-r--r--  1 zabbix zabbix  2037 constants.py
-rwxr-xr-x  1 zabbix zabbix  4614 fiberhome_olt_signals.py
-rwxr-xr-x  1 zabbix zabbix  4622 fiberhome_olt_status.py
-rw-r--r--  1 zabbix zabbix  3939 parsers.py
-rw-r--r--  1 zabbix zabbix  6155 scrapli_client.py
```

---

## ⚙️ Configuração no Zabbix

### Passo 1: Importar o Template

1. Acesse o Zabbix Web UI
2. Vá em **Configuration → Templates**
3. Clique em **Import**
4. Selecione o arquivo `Template Fiberhome.yaml`
5. Clique em **Import**

### Passo 2: Criar o Host da OLT

1. **Configuration → Hosts → Create host**

| Campo | Valor |
|-------|-------|
| Host name | `OLT-Fiberhome-01` |
| Groups | `Network Devices` |
| Interfaces → Agent | IP da OLT |

2. **Vá na aba Templates**

| Campo | Valor |
|-------|-------|
| Link new templates | `Template OLT Fiberhome RP1000` |

3. **Vá na aba Macros**

| Macro | Valor | Descrição |
|-------|-------|-----------|
| `{$SNMP_COMMUNITY}` | `public` | Comunidade SNMP |
| `{$SNMP_PORT}` | `161` | Porta SNMP |
| `{$OLT_USER}` | `GEPON` | Usuário Telnet |
| `{$OLT_PASSWORD}` | `GEPON` | Senha Telnet |
| `{$OLT_PORT}` | `23` | Porta Telnet |

4. Clique em **Add**

### Passo 3: Aguardar descoberta

- A descoberta de PONs roda a cada **1 hora**
- Os itens de status coletam a cada **6 minutos**
- Os sinais ópticos coletam a cada **2 horas**

Para forçar descoberta imediata:
1. **Configuration → Hosts → [OLT] → Discovery**
2. Clique em **Execute now**

---

## 🧪 Testando os Scripts

### Teste de Conectividade SNMP

```bash
snmpwalk -v 1 -c public 186.209.111.0 1.3.6.1.4.1.5875.800.3.9.3.4.1.2
```

**Saída esperada:**
```
iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34078720 = STRING: "PON 1/1"
iso.3.6.1.4.1.5875.800.3.9.3.4.1.2.34603008 = STRING: "PON 1/2"
```

### Teste do LLD (Descoberta de PONs)

```bash
python3 /usr/lib/zabbix/externalscripts/GetPONName.py \
  186.209.111.0 public OLT-TESTE GEPON GEPON 23 161 | jq .
```

**Saída esperada:**
```json
{
  "data": [
    {
      "{#PONNAME}": "1/1",
      "{#PONALIAS}": "",
      "{#PONSLOT}": "1",
      "{#PONPORT}": "1",
      "{#INDEX}": "34078720"
    }
  ]
}
```

### Teste do Status de ONUs

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_status.py \
  186.209.111.0 GEPON GEPON 23 | jq .
```

**Saída esperada:**
```json
{
  "data": {
    "pon_ports": [
      {
        "slot": "1",
        "pon": "1",
        "pon_name": "1/1",
        "online": 45,
        "offline": 2,
        "provisioned": 47
      }
    ],
    "totals": {
      "provisioned": 876,
      "online": 820,
      "offline": 56
    },
    "metadata": {
      "timestamp": "2026-02-18T12:34:56Z",
      "collection_time_ms": 2450,
      "olt_ip": "186.209.111.0",
      "success": true
    }
  }
}
```

### Teste dos Sinais Ópticos

```bash
python3 /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_signals.py \
  186.209.111.0 GEPON GEPON 23 | jq .
```

**Saída esperada:**
```json
{
  "data": {
    "pon_signals": [
      {
        "slot": "1",
        "pon": "1",
        "pon_name": "1/1",
        "best_signal": 21.33,
        "poor_signal": 27.53,
        "median_signal": 23.45,
        "onu_count": 9
      }
    ],
    "metadata": {
      "success": true
    }
  }
}
```

---

## 📊 Métricas Coletadas

### Itens Globais

| Item | Descrição | Unidade |
|------|-----------|---------|
| Total ONUs Provisionadas | Total de ONUs na OLT | count |
| Total ONUs Online | ONUs com status "up" | count |
| Total ONUs Offline | ONUs com status "dn" | count |
| Clientes Total OLT | Contador SNMP geral | count |
| Temperatura da OLT | Temperatura do chassi | °C |
| Uptime da OLT | Tempo de atividade | uptime |

### Itens por PON (via LLD)

| Item | Descrição | Unidade |
|------|-----------|---------|
| ONU Online - PON {#PONNAME} | ONUs online na PON | count |
| ONU Offline - PON {#PONNAME} | ONUs offline na PON | count |
| ONU Provisionadas - PON {#PONNAME} | Total de ONUs na PON | count |
| Melhor Sinal - PON {#PONNAME} | Melhor sinal RX | dBm |
| Pior Sinal - PON {#PONNAME} | Pior sinal RX | dBm |
| Média Sinal - PON {#PONNAME} | Mediana do sinal RX | dBm |

### Triggers

| Trigger | Condição | Severidade |
|---------|----------|------------|
| Sinal Crítico na PON | Pior sinal > 30 dBm | HIGH |

### Gráficos

- **Status ONUs por PON:** Barras empilhadas (Online/Offline)
- **Sinais Ópticos por PON:** Linha temporal (Best/Median/Poor)

---

## 🔄 Migração da Versão Antiga

Se você usava a versão com `zabbix_sender` + cron:

### Passo 1: Fazer backup

```bash
sudo ./deploy.sh --backup
```

### Passo 2: Remover cron antigo

```bash
sudo rm -f /etc/cron.d/TemplateOLT
```

### Passo 3: Importar novo template

- Importe `Template Fiberhome.yaml` no Zabbix
- O novo template substitui o antigo automaticamente

### Passo 4: Validar dados

- Aguarde 10 minutos
- Verifique **Monitoring → Latest Data**
- Compare com dados anteriores

### Passo 5: Limpeza (após 7 dias estável)

```bash
rm -f /usr/lib/zabbix/externalscripts/GetONUOnline.py
rm -f /usr/lib/zabbix/externalscripts/GetONUSignal.py
```

---

## 🔧 Troubleshooting

### Erro: "Python 3.10+ is required"

```bash
# Verificar versão
python3 --version

# Se necessário, instalar Python 3.10+
# Debian/Ubuntu
apt install python3.11

# RHEL/CentOS
yum install python39
```

### Erro: "Connection refused" (Telnet)

```bash
# Testar conectividade
telnet 186.209.111.0 23

# Verificar firewall
iptables -L -n | grep 23
```

### Erro: "Timeout waiting for pattern"

Causa provável: credenciais incorretas ou login lento.

```bash
# Testar login manual
telnet 186.209.111.0 23
# Digite: GEPON <enter>
# Digite: GEPON <enter>
# Deve aparecer: User>
```

### Scripts não aparecem no Zabbix

```bash
# Verificar permissões
ls -la /usr/lib/zabbix/externalscripts/fiberhome/
chown -R zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome/
chmod +x /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_*.py
```

### Verificar logs

```bash
# Logs do Zabbix Server
tail -f /var/log/zabbix/zabbix_server.log | grep -i fiberhome

# Logs do sistema
journalctl -u zabbix-server -f
```

### Debug de script

```bash
# Rodar com verbose
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import sys
sys.path.insert(0, '/usr/lib/zabbix/externalscripts/fiberhome')
from scrapli_client import FiberhomeClient
import asyncio
asyncio.run(FiberhomeClient('186.209.111.0', 'GEPON', 'GEPON', 23).connect())
"
```

---

## 📁 Estrutura de Arquivos

```
/usr/lib/zabbix/externalscripts/
├── GetPONName.py                    # LLD via SNMP
└── fiberhome/
    ├── __init__.py                  # Módulo Python
    ├── constants.py                 # Constantes e patterns
    ├── scrapli_client.py            # Cliente async Telnet
    ├── parsers.py                   # Parsing de output CLI
    ├── fiberhome_olt_status.py      # Master Item: Status
    └── fiberhome_olt_signals.py     # Master Item: Sinais
```

---

## 📝 Comandos CLI da OLT (Referência)

### Login em dois níveis
```
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
```

### Listar ONUs
```
Admin# cd onu
Admin\onu# show authorization slot all pon all
```

### Sinal óptico
```
Admin# cd card
Admin\card# show optic_module_para slot 1 pon 1
```

---

## 📜 Licença

MIT License

---

## 🤝 Contribuições

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'feat: nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📞 Suporte

- **Issues:** [GitHub Issues](https://github.com/flicl/MonitoraFiberhome/issues)
- **Autor:** [@flicl](https://github.com/flicl)


