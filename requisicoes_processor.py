from flask import Flask, jsonify, request
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "API funcionando!"})

@app.route('/processar', methods=['POST'])
def processar():
    try:
        dados = request.get_json()
        mensagem = dados.get('mensagem', 'sem mensagem')
        
        resposta = {
            "status": "recebido",
            "mensagem_recebida": mensagem,
            "tipo": "TESTE"
        }
        
        return jsonify(resposta), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Iniciando na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)