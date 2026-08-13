import os
import gc
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def consultar_gemini_dinamico(prompt):
    if not GEMINI_API_KEY:
        raise Exception("No se encontró la variable GEMINI_API_KEY en las configuraciones de Render.")

    # 1. Consultar el catálogo dinámico de modelos activos en Google
    url_listado = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    modelos_disponibles = []
    
    try:
        print("Obteniendo catálogo dinámico de modelos activos...")
        res_list = requests.get(url_listado, timeout=10)
        if res_list.status_code == 200:
            data_list = res_list.json()
            for m in data_list.get("models", []):
                metodos = m.get("supportedGenerationMethods", [])
                if "generateContent" in metodos:
                    modelos_disponibles.append(m["name"])
            print(f"Modelos activos encontrados: {modelos_disponibles}")
    except Exception as e:
        print(f"No se pudo consultar el catálogo dinámico: {e}")

    # Respaldos manuales por si falla la llamada al catálogo
    if not modelos_disponibles:
        modelos_disponibles = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    ultimo_error = ""

    # 2. Intentar la generación con el primer modelo funcional de la lista devuelta por Google
    for nombre_modelo in modelos_disponibles:
        if not nombre_modelo.startswith("models/"):
            nombre_modelo = f"models/{nombre_modelo}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{nombre_modelo}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            print(f"Probando modelo: {nombre_modelo}...")
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            data = res.json()

            if res.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        texto = parts[0]["text"]
                        print(f"¡Respuesta exitosa recibida de {nombre_modelo}!")
                        return texto
            else:
                msg = data.get("error", {}).get("message", res.text)
                print(f"Error {res.status_code} en {nombre_modelo}: {msg}")
                ultimo_error = msg
        except Exception as e:
            print(f"Excepción en {nombre_modelo}: {e}")
            ultimo_error = str(e)

    raise Exception(f"Ningún modelo disponible respondió. Último error: {ultimo_error}")

@app.route('/', methods=['GET'])
def home():
    return "Servidor del Asistente Activo y Funcionando", 200

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json(silent=True) or {}
        pregunta = data.get('pregunta', '')

        if not pregunta:
            return jsonify({"error": "No se recibió ninguna pregunta"}), 400

        print(f"Pregunta recibida: {pregunta}")

        prompt = f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        
        # Consultar Gemini usando detección dinámica
        texto_respuesta = consultar_gemini_dinamico(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Crear audio MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        gc.collect()

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        
        tts = gTTS(text="Ocurrió un error al consultar la inteligencia artificial.", lang='es')
        tts.save("respuesta.mp3")
        gc.collect()
        
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def obtener_audio():
    if os.path.exists("respuesta.mp3"):
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
    return "Archivo de audio no encontrado", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
