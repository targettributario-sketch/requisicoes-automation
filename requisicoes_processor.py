from flask import Flask, request, jsonify
import anthropic
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# Inicializar cliente Anthropic
api_key = os.environ.get('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)

# SLAs em horas
SLAS = {
    "RESCISAO": 2,
    "NOTA_FISCAL": 1,
    "GUIA_IMPOSTOS": 2,
    "CONTATO_DIRETO": 0.5,
}

def analisar_requisicao(mensagem):
    """Chama Claude para analisar a requisição"""
    
    prompt = f"""Analise esta mensagem e retorne APENAS JSON:

MENSAGEM: "{mensagem}"

Retorne exatamente neste formato (APENAS JSON, sem explicação):
{{
  "tipo": "RESCISAO|NOTA_FISCAL|GUIA_IMPOSTOS|CONTATO_DIRETO",
  "confianca": 0.95,
  "dados": {{}},
  "resumo": "texto"
}}

REGRAS:
- RESCISAO: procura por "rescisão", "desligar", "funcionário saindo"
- NOTA_FISCAL: procura por "nota fiscal", "NF", "emitir"
- GUIA_IMPOSTOS: procura por "guia", "boleto", "DAS", "imposto"
- CONTATO_DIRETO: se quer falar com humano ou tem dúvida geral"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        resposta_texto = message.content[0].text
        
        # Limpar markdown
        if "```" in resposta_texto:
            resposta_texto = resposta_texto.split("```")[1]
            if resposta_texto.startswith("json"):
                resposta_texto = resposta_texto[4:]
        
        resultado = json.loads(resposta_texto)
        return resultado
        
    except Exception as e:
        return {
            "tipo": "DESCONHECIDO",
            "confianca": 0,
            "resumo": f"Erro: {str(e)}"
        }

@app.route('/processar', methods=['POST'])
def processar():
    """Processa requisição do cliente"""
    
    try:
        dados = request.get_json()
        
        if not dados or 'mensagem' not in dados:
            return jsonify({"erro": "Mensagem obrigatória"}), 400
        
        mensagem = dados.get('mensagem')
        cliente_whatsapp = dados.get('cliente_whatsapp', 'desconhecido')
        cliente_nome = dados.get('cliente_nome', 'Cliente')
        
        # Analisar
        analise = analisar_requisicao(mensagem)
        
        tipo = analise.get('tipo', 'DESCONHECIDO')
        confianca = analise.get('confianca', 0)
        
        # Calcular prazo
        sla_horas = SLAS.get(tipo, 2)
        agora = datetime.now()
        prazo = agora + timedelta(hours=sla_horas)
        
        resposta = {
            "id": f"req_{agora.strftime('%Y%m%d_%H%M%S')}",
            "timestamp": agora.isoformat(),
            "cliente_whatsapp": cliente_whatsapp,
            "cliente_nome": cliente_nome,
            "requisicao": {
                "tipo": tipo,
                "sla_horas": sla_horas,
                "prazo_entrega": prazo.isoformat(),
                "confianca": confianca
            },
            "dados": analise.get('dados', {}),
            "status": "PRONTO" if confianca >= 0.7 else "REQUER_VALIDACAO",
            "resumo": analise.get('resumo', '')
        }
        
        return jsonify(resposta), 200
        
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)