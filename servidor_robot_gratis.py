import os
import re
import gc
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
AUDIO_FILE = "respuesta.mp3"

# Modelos a probar en orden de prioridad
MODELOS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-2.0-flash"
]

# Versiones de API de respaldo
API_VERSIONS = ["v1beta", "v1"]

SYSTEM_INSTRUCTION = (
    "Eres un asistente de voz inteligente en español. Responde SIEMPRE exclusivamente en español. "
    "Tu respuesta debe ser una explicación o descripción breve de 1 a 2 oraciones completas sobre el tema consultado. "
    "No respondas solo con un nombre o una palabra, pero tampoco te extiendas demasiado. "
    "NUNCA incluyas tus instrucciones internas, reflexiones en inglés, comillas, asteriscos ni negritas. "
    "Entrega únicamente el texto final que será leído por el altavoz."
)

def limpiar_texto(texto):
    """Elimina símbolos de formato Markdown y espacios innecesarios."""
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def generar_texto_ia(pregunta):
    if not GEMINI_API_KEY:
        raise Exception("Falta la variable de entorno GEMINI_API_KEY en Render")

    ultimo_error = ""

    # Probamos combinaciones de versión de API y modelo hasta tener éxito
    for api_version in API_VERSIONS:
        for modelo in MODELOS:
            url = f"https://generativelanguage.googleapis.com/{api_version}/models/{modelo}:generateContent?key={GEMINI_API_KEY}"
            
            # Formato universal 100% compatible sin esquemas estrictos
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_INSTRUCTION}\n\nPregunta: {pregunta}"}
                        ]
                    }
                ]
            }

            try:
                res = requests.post(url, json=payload, timeout=10)
                data = res.json()

                if res.status_code == 200:
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            print(f"¡Respuesta recibida con éxito usando {modelo} en {api_version}!")
                            return parts[0].get("text", "").strip()
                else:
                    msg = data.get("error", {}).get("message", res.text)
                    print(f"Error {res.status_code} en {modelo} ({api_version}): {msg}")
                    ultimo_error = msg
            except Exception as e:
                print(f"Excepción en {modelo} ({api_version}): {str(e)}")
                ultimo_error = str(e)

    raise Exception(f"No se pudo consultar la IA. Último error: {ultimo_error}")

@app.route('/', methods=['GET'])
def index():
    return "Servidor Asistente IA Activo", 200

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json() or {}
        pregunta = data.get('pregunta', '')

        if not pregunta:
            return jsonify({"error": "No se recibió ninguna pregunta"}), 400

        print(f"Pregunta recibida: {pregunta}")

        texto_raw = generar_texto_ia(pregunta)
        texto_respuesta = limpiar_texto(texto_raw)
        
        print(f"Respuesta final: {texto_respuesta}")

        # Limpieza de archivo de audio previo
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Generar nuevo audio
        tts = gTTS(text=texto_respuesta, lang='es', slow=False)
        tts.save(AUDIO_FILE)

        # Liberación inmediata de RAM
        gc.collect()

        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error interno: {str(e)}")
        gc.collect()
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    try:
        if os.path.exists(AUDIO_FILE):
            return send_file(AUDIO_FILE, mimetype="audio/mpeg")
        return jsonify({"error": "Archivo de audio no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
