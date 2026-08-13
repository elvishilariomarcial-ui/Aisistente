import os
import gc
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

app = Flask(__name__)

# Clave API de Gemini cargada desde las variables de entorno de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def consultar_gemini(prompt):
    if not GEMINI_API_KEY:
        raise Exception("No se encontró la variable GEMINI_API_KEY en las configuraciones de Render.")

    # Lista de endpoints y versiones a probar secuencialmente
    intentos = [
        ("v1beta", "gemini-1.5-flash"),
        ("v1", "gemini-1.5-flash"),
        ("v1beta", "gemini-1.5-flash-latest"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1beta", "gemini-1.5-pro")
    ]

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    ultimo_error = ""

    for version, modelo in intentos:
        url = f"https://generativelanguage.googleapis.com/{version}/models/{modelo}:generateContent?key={GEMINI_API_KEY}"
        try:
            print(f"Probando versión {version} con modelo {modelo}...")
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            data = res.json()

            if res.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        texto = parts[0]["text"]
                        print(f"¡Respuesta exitosa con {modelo} ({version})!")
                        return texto
            else:
                msg = data.get("error", {}).get("message", res.text)
                print(f"Respuesta {res.status_code} en {modelo}: {msg}")
                ultimo_error = msg
        except Exception as e:
            print(f"Excepción al conectar con {modelo}: {e}")
            ultimo_error = str(e)

    raise Exception(f"Ningún modelo de Gemini respondió. Último mensaje: {ultimo_error}")

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
        
        # Petición HTTP directa a la API de Gemini
        texto_respuesta = consultar_gemini(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Conversión de texto a voz MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        # Liberar memoria RAM
        gc.collect()

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        
        # Audio de voz de respaldo
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
