# xBattery Pilot

Integração custom para Home Assistant que planeia a carga noturna da bateria (inversores híbridos Deye) com base na previsão solar, no histórico de consumo e nas tarifas tri-horárias.

> v0.1 - só leitura: calcula o plano e expõe sensores, ainda não controla o inversor.

## Funcionalidades
- Previsão de consumo a partir das estatísticas do sensor de carga (média ponderada 1–7, 7 e 14 dias)
- Previsão solar via Forecast.Solar, Solcast ou Open-Meteo Solar Forecast
- Simulação do SOC em intervalos de 30 min
- Escolha do SOC alvo que minimiza o custo (vazio/cheias/ponta) com injeção zero
- Sensores: plano, SOC alvo, carga pela rede, custo e poupança previstos, solar/consumo previstos, SOC mínimo, solar desperdiçado

## Instalação (HACS)
1. HACS → ⋮ → Repositórios personalizados → `https://github.com/BTNBx/xbattery-pilot` (Integração)
2. Instalar **xBattery Pilot** e reiniciar o Home Assistant
3. Definições → Dispositivos e serviços → Adicionar integração → **xBattery Pilot**

## Cartão
`xbattery-pilot-card.js` (pasta `dist/`) — `type: custom:xbattery-pilot-card`
