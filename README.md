# Template OLT Fiberhome RP1000 para Zabbix
**Modelo confirmado: AN5116-06B / AN5516-01**

Monitoramento de OLTs Fiberhome via Zabbix, com descoberta automática de portas PON (SNMP LLD) e coleta de métricas de ONUs via Telnet.

## Arquitetura (v2.0)

```
Zabbix Server (Pull Model)
  ├─ GetPONName.py (EXTERNAL, 1h) → JSON LLD [SNMP]
  ├─ fiberhome_olt_status.py (EXTERNAL, 6m) → JSON Master Item
  │    └─ Dependent Items: OntOnline, OntOffline, OntProvisioned (por PON)
  └─ fiberhome_olt_signals.py (EXTERNAL, 2h) → JSON Master Item
       └─ Dependent Items: OntBestSinal, OntPoorSinal, OntMediaSinal (por PON)
```

**Benefícios da nova arquitetura:**
- ✅ Zero zabbix_sender (push passivo → pull ativo)
- ✅ Zero cron dependencies
- ✅ Uma conexão Telnet por coleta
- ✅ Async/await para I/O não-bloqueante
- ✅ JSON testável manualmente
- ✅ Python 3.10+ (stdlib only, sem dependências externas)

## Instalação

### Método 1: Script de Deploy (Recomendado)

```sh
# Clone o repositório
git clone https://github.com/netoadmredes/template-olt_fiberhome
cd template-olt_fiberhome

# Execute o deploy (como root)
sudo ./deploy.sh --backup

# O script:
# - Verifica Python >= 3.10
# - Copia scripts para /usr/lib/zabbix/externalscripts/fiberhome/
# - Configura permissões
# - Faz backup dos scripts legados (com --backup)
```

### Método 2: Manual

```sh
# Dependências (Python 3.10+ é o único requisito)
python3 --version  # deve ser >= 3.10

# Instalar os scripts
mkdir -p /usr/lib/zabbix/externalscripts/fiberhome
cp fiberhome/*.py /usr/lib/zabbix/externalscripts/fiberhome/
cp GetPONName.py /usr/lib/zabbix/externalscripts/
chmod +x /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_*.py
chmod +x /usr/lib/zabbix/externalscripts/GetPONName.py
chown -R zabbix:zabbix /usr/lib/zabbix/externalscripts/fiberhome
```

## Configuração no Zabbix

### 1. Importar o Template
1. No Zabbix, vá em **Configuration > Templates > Import**.
2. Selecione o arquivo `Template Fiberhome.yaml`.
3. Clique em **Import**.
4. Associe o template `Template OLT Fiberhome RP1000` ao seu host.

### 2. Configurar Macros do Host

| Macro | Valor padrão | Descrição |
|---|---|---|
| `{$SNMP_COMMUNITY}` | `public` | Community SNMP |
| `{$SNMP_PORT}` | `161` | Porta SNMP |
| `{$OLT_USER}` | `GEPON` | Usuário Telnet |
| `{$OLT_PASSWORD}` | `GEPON` | Senha Telnet |
| `{$OLT_PORT}` | `23` | Porta Telnet |

### 3. Itens do Template

#### Master Items (EXTERNAL)
| Nome | Chave | Intervalo | Output |
|---|---|---|---|
| OLT Status - Master Item | `fiberhome_olt_status.py[...]` | 6m | JSON |
| OLT Signals - Master Item | `fiberhome_olt_signals.py[...]` | 2h | JSON |
| PON Discovery | `GetPONName.py[...]` | 1h | JSON LLD |

#### Dependent Items (extraem do JSON via JSONPath)
| Chave | JSONPath | Master Item |
|---|---|---|
| `TotalOntOnline` | `$.data.totals.online` | Status |
| `TotalOntOffline` | `$.data.totals.offline` | Status |
| `TotalOntProvisioned` | `$.data.totals.provisioned` | Status |
| `OntOnline.[{#PONNAME}]` | `$.data.pon_ports[?(@.pon_name=='{#PONNAME}')].online` | Status |
| `OntBestSinal.[{#PONNAME}]` | `$.data.pon_signals[?(@.pon_name=='{#PONNAME}')].best_signal` | Signals |

## JSON Output Schema

### fiberhome_olt_status.py
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

### fiberhome_olt_signals.py
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
      "timestamp": "2026-02-18T12:34:56Z",
      "collection_time_ms": 8500,
      "olt_ip": "186.209.111.0",
      "success": true
    }
  }
}
```

## Testando Manualmente

```sh
# Testar coleta de status
python3 /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_status.py \
  186.209.111.0 GEPON GEPON 23 | jq .

# Testar coleta de sinais
python3 /usr/lib/zabbix/externalscripts/fiberhome/fiberhome_olt_signals.py \
  186.209.111.0 GEPON GEPON 23 | jq .

# Testar LLD SNMP
python3 /usr/lib/zabbix/externalscripts/GetPONName.py \
  186.209.111.0 public OLT_HOSTNAME GEPON GEPON 23 161 | jq .
```

## Migração da Versão Legada

Se você estava usando a versão anterior (com zabbix_sender + cron):

```sh
# 1. Fazer backup dos scripts legados
sudo ./deploy.sh --backup

# 2. Remover entradas de cron
sudo rm -f /etc/cron.d/TemplateOLT

# 3. Importar novo template YAML no Zabbix

# 4. Após 7 dias de operação estável, remover scripts legados
rm -f /usr/lib/zabbix/externalscripts/GetONUOnline.py
rm -f /usr/lib/zabbix/externalscripts/GetONUSignal.py
```

## Estrutura de Arquivos

```
/usr/lib/zabbix/externalscripts/
├── GetPONName.py                    # LLD SNMP
└── fiberhome/
    ├── __init__.py
    ├── constants.py                 # Timeouts, patterns
    ├── scrapli_client.py            # Cliente async Telnet
    ├── parsers.py                   # Parsing de output CLI
    ├── fiberhome_olt_status.py      # Master: Online/Offline/Provisioned
    └── fiberhome_olt_signals.py     # Master: Sinais ópticos
```

## Comandos CLI Confirmados (Fiberhome AN5116-06B / AN5516-01)

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

### Sinal óptico por PON
```
Admin# cd card
Admin\card# show optic_module_para slot 1 pon 1
```

### Encerramento de sessão
```
Admin# quit
User> quit
```

## Troubleshooting

### Erro de conexão
```sh
# Verificar conectividade
telnet 186.209.111.0 23

# Verificar credenciais
python3 -c "
import asyncio
from fiberhome.scrapli_client import FiberhomeClient
asyncio.run(FiberhomeClient('IP', 'USER', 'PASS', 23).connect())
"
```

### Logs
Os scripts logam para stderr (stdout é reservado para JSON):

```sh
# Ver logs em tempo real
journalctl -u zabbix-server -f | grep -i fiberhome
```

## Licença

MIT License - Veja arquivo LICENSE para detalhes.
