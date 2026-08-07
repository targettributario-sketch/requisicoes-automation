"""
Requisições Contábeis - Processador de Automação
Sistema de IA para identificar e estruturar requisições contábeis

Autor: Seu Nome
Versão: 1.0
"""

from flask import Flask, request, jsonify
from anthropic import Anthropic
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Inicializar cliente Anthropic
client = Anthropic()

# Configuração de SLAs (em horas)
SLAS = {
    "RESCISAO": 2,
    "NOTA_FISCAL": 1,
    "GUIA_IMPOSTOS": 2,
    "CONTATO_DIRETO": 0.5,  # Notifica imediatamente
}

# Templates de resposta automática
TEMPLATES = {
    "RESCISAO": """Oi! 👋 Recebemos sua rescisão!

📋 Tipo: Rescisão
👤 Funcionário: {nome_funcionario}
📅 Data de Saída: {data_saida}
🏢 Motivo: {motivo}

⏰ Recebido às: {hora_atual}
⏱️ Entrega estimada: até {hora_entrega}

Vamos processar com atenção. Qualquer dúvida, entramos em contato!

Abs,
Anderson""",

    "NOTA_FISCAL": """Oi! 📄 Recebemos sua NF!

📋 Serviço: {descricao}
💰 Valor: R$ {valor}
🏢 Cliente: {cliente_destino}

⏰ Recebido às: {hora_atual}
⏱️ Entrega estimada: até {hora_entrega}

Vamos gerar e enviar com rapidez. Bora!

Abs,
Anderson""",

    "GUIA_IMPOSTOS": """Oi! 💼 Recebemos sua solicitação de guia!

📋 Período: {mes_periodo}
🏦 Imposto: {tipo_imposto}

⏰ Recebido às: {hora_atual}
⏱️ Entrega estimada: até {hora_entrega}

Validamos no ONVIO e enviamos para você!

Abs,
Anderson""",

    "CONTATO_DIRETO": """Oi! 👋 Entendi que você quer falar com a gente!

Um momento que transferimos para o Anderson ou Simone responder sua dúvida.

Obrigado por entrar em contato! 🙌"""
}


def calcular_prazo_entrega(sla_horas):
    """Calcula data/hora de entrega baseado no SLA"""
    agora = datetime.now()
    prazo = agora + timedelta(hours=sla_horas)
    return prazo.isoformat()


def formatar_hora(dt_string):
    """Formata datetime para horário legível"""
    dt = datetime.fromisoformat(dt_string)
    return dt.strftime("%H:%M")


def analisar_com_claude(mensagem_cliente):
    """
    Chama Claude API para analisar a requisição
    Retorna JSON estruturado com tipo e dados
    """
    
    prompt_sistema = """Você é um especialista em análise de requisições contábeis.

Analise a mensagem do cliente e identifique:

1. TIPO DE REQUISIÇÃO:
   - RESCISÃO: quando fala em "rescisão", "desligar", "funcionário saindo"
   - NOTA_FISCAL: quando pede "nota fiscal", "NF", "emitir nota"
   - GUIA_IMPOSTOS: quando pede "guia", "boleto", "ONVIO", "pagamento imposto", "DAS"
   - CONTATO_DIRETO: quando quer falar com humano, pede "suporte", "dúvida", "falar com", "humano"

2. CAMPOS OBRIGATÓRIOS (extraia com precisão):
   - RESCISÃO: nome_funcionario, data_saida (DD/MM/YYYY), motivo (pedido/dispensa)
   - NOTA_FISCAL: descricao, valor (número), cliente_destino
   - GUIA_IMPOSTOS: mes_periodo (MM/YYYY), tipo_imposto (DAS/ICMS/ISS/PIS/IRPJ/CSLL)
   - CONTATO_DIRETO: motivo_contato (resumo do que quer)

3. NÍVEL DE CONFIANÇA (0-1): quão certo você está da classificação

IMPORTANTE: Retorne APENAS JSON, sem explicação, markdown ou preamble.

Formato obrigatório:
{
  "tipo": "RESCISAO|NOTA_FISCAL|GUIA_IMPOSTOS|CONTATO_DIRETO",
  "confianca": 0.95,
  "dados": {
    "campo1": "valor1",
    "campo2": "valor2"
  },
  "campos_faltando": ["campo_x", "campo_y"],
  "resumo": "O que você entendeu da requisição"
}"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=500,
            system=prompt_sistema,
            messages=[
                {
                    "role": "user",
                    "content": f"Analise esta mensagem: {mensagem_cliente}"
                }
            ]
        )
        
        # Extrair resposta
        resposta_texto = message.content[0].text
        
        # Limpar markdown se houver
        if resposta_texto.startswith("```json"):
            resposta_texto = resposta_texto[7:]
        if resposta_texto.startswith("```"):
            resposta_texto = resposta_texto[3:]
        if resposta_texto.endswith("```"):
            resposta_texto = resposta_texto[:-3]
        
        resposta_json = json.loads(resposta_texto.strip())
        return resposta_json
        
    except json.JSONDecodeError as e:
        return {
            "tipo": "DESCONHECIDO",
            "confianca": 0.0,
            "erro": f"Erro ao parsear resposta: {str(e)}"
        }
    except Exception as e:
        return {
            "tipo": "DESCONHECIDO",
            "confianca": 0.0,
            "erro": str(e)
        }


@app.route('/processar', methods=['POST'])
def processar_requisicao():
    """
    Endpoint principal que recebe mensagem do Make
    e retorna JSON estruturado
    
    Espera:
    {
        "cliente_whatsapp": "+5511999999999",
        "cliente_nome": "Empresa XYZ",
        "mensagem": "Preciso de rescisão do João"
    }
    """
    
    try:
        dados = request.get_json()
        
        if not dados or 'mensagem' not in dados:
            return jsonify({"erro": "Mensagem obrigatória"}), 400
        
        mensagem = dados.get('mensagem')
        cliente_whatsapp = dados.get('cliente_whatsapp', 'desconhecido')
        cliente_nome = dados.get('cliente_nome', 'Cliente')
        
        # Analisar com Claude
        analise = analisar_com_claude(mensagem)
        
        tipo = analise.get('tipo', 'DESCONHECIDO')
        confianca = analise.get('confianca', 0)
        dados_extraidos = analise.get('dados', {})
        campos_faltando = analise.get('campos_faltando', [])
        
        # Calcular SLA
        sla_horas = SLAS.get(tipo, 2)
        prazo_entrega = calcular_prazo_entrega(sla_horas)
        hora_entrega = formatar_hora(prazo_entrega)
        hora_atual = datetime.now().strftime("%H:%M")
        
        # Gerar resposta automática
        if tipo in TEMPLATES:
            template = TEMPLATES[tipo]
            try:
                resposta_automatica = template.format(
                    **dados_extraidos,
                    hora_atual=hora_atual,
                    hora_entrega=hora_entrega
                )
            except KeyError:
                resposta_automatica = template
        else:
            resposta_automatica = TEMPLATES.get("CONTATO_DIRETO", "")
        
        # Montar resposta final
        resposta = {
            "id": f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "cliente_whatsapp": cliente_whatsapp,
            "cliente_nome": cliente_nome,
            
            "requisicao": {
                "tipo": tipo,
                "sla_horas": sla_horas,
                "prazo_entrega": prazo_entrega,
                "confianca": confianca
            },
            
            "dados": dados_extraidos,
            "campos_faltando": campos_faltando,
            
            "status": "PRONTO_PARA_PROCESSAR" if confianca >= 0.7 else "REQUER_VALIDACAO",
            "resposta_automatica": resposta_automatica,
            
            "resumo": analise.get('resumo', ''),
            "errro": analise.get('erro')
        }
        
        return jsonify(resposta), 200
        
    except Exception as e:
        return jsonify({
            "erro": str(e),
            "tipo": "ERRO_PROCESSAMENTO"
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check para Railway"""
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    # Railway usa PORT da env
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
