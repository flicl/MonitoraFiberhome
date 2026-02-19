# Deprecated Files

Esta pasta contém arquivos obsoletos que foram substituídos por novas implementações.

## discovery_interfaces.py
Substituído por `fiberhome/interfaces.py` e `fiberhome_olt_interfaces.py`.
- Nova versão segue padrões do projeto (type hints, estrutura de módulos)
- Usa subprocess para snmpwalk de forma mais robusta
- Retorno em formato Zabbix LLD correto

## discovery_interfaces_exe.sh
Substituído por `fiberhome_olt_interfaces.py`.
- Wrapper Python é mais consistente com o restante do projeto
- Não requer script bash separado

## Template Interfaces Fisicas OLT by SNMP - BEE.yaml
Substituído pela integração ao `Template Fiberhome.yaml`.
- Template estava em Zabbix 6.0 (projeto usa 7.0)
- Discovery de interfaces físicas agora está integrado ao template principal
- Evita duplicação de templates
