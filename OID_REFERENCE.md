# TriplePlay - Referencia de OIDs Fiberhome

Este documento contem todos os OIDs utilizados nos templates TriplePlay para monitoramento de OLTs Fiberhome.

## Informacoes do Sistema

| OID | Nome | Tipo | Descricao |
|-----|------|------|-----------|
| 1.3.6.1.2.1.1.1.0 | sysDescr | String | Descricao do sistema |
| 1.3.6.1.2.1.1.3.0 | sysUpTime | TimeTicks | Tempo de atividade (centesimos de segundo) |
| 1.3.6.1.2.1.1.5.0 | sysName | String | Nome do sistema |
| 1.3.6.1.2.1.1.6.0 | sysLocation | String | Localizacao |

## Chassis

| OID | Nome | Tipo | Descricao |
|-----|------|------|-----------|
| .1.3.6.1.4.1.5875.800.3.9.4.5.0 | sysTemperature | Integer | Temperatura interna (Celsius) |
| .1.3.6.1.4.1.5875.800.3.60.2.1.1.21 | fanAlarmStatus | Integer | Status dos fans |

### Valores de fanAlarmStatus

| Valor | Significado |
|-------|-------------|
| 1 | Normal |
| 2 | Parado |
| 3 | Anormal |
| 4 | Nao Monitorado |

## Cards GPON (Tabela: .1.3.6.1.4.1.5875.800.3.9.2.1.1)

| OID Sufixo | Nome | Tipo | Descricao |
|------------|------|------|-----------|
| .1.{INDEX} | cardIndex | Integer | Indice do card |
| .2.{INDEX} | cardType | Integer | Tipo do card |
| .3.{INDEX} | cardHardwareVersion | String | Versao de hardware |
| .4.{INDEX} | cardSoftwareVersion | String | Versao de software |
| .5.{INDEX} | cardStatus | Integer | Status operacional |
| .6.{INDEX} | cardNumOfPorts | Integer | Numero de portas |
| .7.{INDEX} | cardAvaliablePorts | Integer | Portas disponiveis |
| .8.{INDEX} | cardCpuUtil | Integer | Uso de CPU (x0.01 = %) |
| .9.{INDEX} | cardMenUtil | Integer | Uso de memoria (x0.01 = %) |

### Valores de cardType

| Valor | Modelo |
|-------|--------|
| 415 | HU1A |
| 527 | GC8B |
| 550 | GCOB |

## Management Cards (Tabela: .1.3.6.1.4.1.5875.800.3.9.8.1.1)

| OID Sufixo | Nome | Tipo | Descricao |
|------------|------|------|-----------|
| .1.{INDEX} | mgrCardType | Integer | Tipo do card |
| .4.{INDEX} | mgrCardWorkStatus | Integer | Status de trabalho |
| .5.{INDEX} | mgrCardCpuUtil | Integer | Uso de CPU (x0.01 = %) |
| .6.{INDEX} | mgrCardMemUtil | Integer | Uso de memoria (x0.01 = %) |

### Valores de mgrCardType

| Valor | Modelo |
|-------|--------|
| 355 | HSWA |
| 374 | HSUB |
| 365 | WSWD |

## Portas GPON (Tabela: .1.3.6.1.4.1.5875.800.3.9.3.4.1)

**IMPORTANTE:** Estes OIDs substituem o script `ponfh.sh`

| OID Sufixo | Nome | Tipo | Descricao |
|------------|------|------|-----------|
| .2.{INDEX} | oltPonSlotPort | String | Slot/Porta (ex: 2/1) |
| .3.{INDEX} | oltPonDesc | String | Descricao da porta |
| .5.{INDEX} | oltPonStatus | Integer | Status da porta (0=Down, 1=Up) |
| .7.{INDEX} | oltPonOnuOnlineNum | Integer | **ONUs Online** |
| .8.{INDEX} | oltPonOnuOfflineNum | Integer | **ONUs Offline** |
| .9.{INDEX} | oltPonOnuLosNum | Integer | **ONUs LOS** |
| .10.{INDEX} | oltPonOnuNodataNum | Integer | **ONUs Sem Dados** |
| .11.{INDEX} | oltPonOnuDyinggaspNum | Integer | **ONUs DyingGasp** |
| .12.{INDEX} | oltPonAuthOnuNum | Integer | **ONUs Autorizadas** |

### Mapeamento Status ONU (ponfh.sh -> SNMP)

| ponfh.sh STATUS | SNMP OID | Descricao |
|-----------------|----------|-----------|
| 0 (LOS) | .9.{INDEX} | Loss of Signal |
| 1 (Online) | .7.{INDEX} | Online |
| 2 (Offline) | .8.{INDEX} | Offline |
| 3 (Sem Dados) | .10.{INDEX} | Sem Dados |
| 4 (DyingGasp) | .11.{INDEX} | DyingGasp/Energia |

### Exemplo de Query SNMP

```bash
# Substitui: ponfh.sh "2/1" 1 "192.168.0.10"
# Por:
snmpget -v 2c -c public 192.168.0.10 .1.3.6.1.4.1.5875.800.3.9.3.4.1.7.X

# Onde X e o INDEX correspondente a porta 2/1
# Descobrir INDEX:
snmpwalk -v 2c -c public 192.168.0.10 .1.3.6.1.4.1.5875.800.3.9.3.4.1.2
```

## ONUs Individuais (Tabela: .1.3.6.1.4.1.5875.800.3.9.3.3.1)

| OID Sufixo | Nome | Tipo | Descricao |
|------------|------|------|-----------|
| .2.{INDEX} | onuIndex | Integer | ID da ONU |
| .6.{INDEX} | onuRxPower | Integer | Potencia RX (x0.01 = dBm) |
| .7.{INDEX} | onuTxPower | Integer | Potencia TX (x0.01 = dBm) |

### Informacoes Adicionais da ONU (Tabela: .1.3.6.1.4.1.5875.800.3.10.1.1)

| OID Sufixo | Nome | Tipo | Descricao |
|------------|------|------|-----------|
| .2.{INDEX} | onuSlot | Integer | Slot da ONU |
| .3.{INDEX} | onuPort | Integer | Porta da ONU |
| .10.{INDEX} | onuSerial | String | Numero de serie |
| .11.{INDEX} | onuStatus | Integer | Status operacional |
| .15.{INDEX} | onuDistance | Integer | Distancia (metros) |

### Valores de onuStatus

| Valor | Significado |
|-------|-------------|
| 0 | LOS (Loss of Signal) |
| 1 | Online |
| 2 | Offline |
| 3 | Sem Dados |
| 4 | DyingGasp (Falta de Energia) |

### Exemplo: Interpretar RX Power

```bash
# Valor bruto SNMP: -2800
# Calculo: -2800 * 0.01 = -28.00 dBm

# No Zabbix, usar preprocessing:
# Multiplier: 0.01
```

## Interfaces de Rede (IF-MIB)

| OID | Nome | Tipo | Descricao |
|-----|------|------|-----------|
| 1.3.6.1.2.1.2.2.1.2.{INDEX} | ifDescr | String | Descricao |
| 1.3.6.1.2.1.2.2.1.3.{INDEX} | ifType | Integer | Tipo |
| 1.3.6.1.2.1.2.2.1.5.{INDEX} | ifSpeed | Gauge | Velocidade (bps) |
| 1.3.6.1.2.1.2.2.1.8.{INDEX} | ifOperStatus | Integer | Status operacional |
| 1.3.6.1.2.1.31.1.1.1.1.{INDEX} | ifName | String | Nome |
| 1.3.6.1.2.1.31.1.1.1.6.{INDEX} | ifHCInOctets | Counter64 | Bytes recebidos |
| 1.3.6.1.2.1.31.1.1.1.10.{INDEX} | ifHCOutOctets | Counter64 | Bytes enviados |
| 1.3.6.1.2.1.31.1.1.1.15.{INDEX} | ifHighSpeed | Gauge | Velocidade (Mbps) |

### Valores de ifOperStatus

| Valor | Significado |
|-------|-------------|
| 1 | Up |
| 2 | Down |
| 3 | Testing |
| 4 | Unknown |
| 5 | Dormant |
| 6 | NotPresent |
| 7 | LowerLayerDown |

## Testes de Conectividade

### Teste Basico

```bash
# Testar se SNMP responde
snmpget -v 2c -c public 192.168.x.x 1.3.6.1.2.1.1.1.0

# Listar todas as portas GPON
snmpwalk -v 2c -c public 192.168.x.x .1.3.6.1.4.1.5875.800.3.9.3.4.1.2

# Contar ONUs online de todas as portas
snmpwalk -v 2c -c public 192.168.x.x .1.3.6.1.4.1.5875.800.3.9.3.4.1.7
```

### Teste de Performance

```bash
# Medir tempo de resposta
time snmpwalk -v 2c -c public 192.168.x.x .1.3.6.1.4.1.5875.800.3.9.3.4.1.2

# Se demorar mais de 30s, aumentar timeout no Zabbix
```

### Troubleshooting

| Problema | Causa Provavel | Solucao |
|----------|----------------|---------|
| Timeout SNMP | Firewall ou OLT sobrecarregada | Aumentar timeout, verificar regras |
| Community incorreta | Configuracao errada | Verificar community string |
| OID nao encontrado | Versao de firmware diferente | Consultar MIB especifica |
| Valores zerados | ONU sem trafego | Normal para ONUs inativas |

---
**Versao:** 1.0.0
**Compatibilidade:** AN5116, AN6000 series
