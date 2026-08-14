import os
import re
import gc
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
AUDIO_FILE = "respuesta.mp3"

SYSTEM_INSTRUCTION = (
    "Eres un asistente de voz inteligente en español. Responde SIEMPRE exclusivamente en español. "
    "Tu respuesta debe ser una explicación o descripción breve de 1 a 2 oraciones completas sobre el tema consultado. "
    "No respondas solo con un nombre o una palabra, pero tampoco te extiendas demasiado. "
    "NUNCA incluyas tus instrucciones internas, reflexiones en inglés, comillas, asteriscos ni negritas. "
    "Entrega únicamente el texto final que será leído por el altavoz."
)

def limpiar_texto(texto):
    """Elimina formato Markdown y caracteres especiales."""
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def obtener_modelo_y_version():
    """Consulta dinámicamente a la API de Google qué modelos están disponibles para tu API Key."""
    for api_version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={GEMINI_API_KEY}"
        try:
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                models = res.json().get("models", [])
                candidatos = []
                for m in models:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        name = m.get("name") # Retorna el nombre completo (ej. "models/gemini-1.5-flash")
                        candidatos.append((api_version, name))
                
                # Priorizar modelos rápidos de tipo 'flash'
                for ver, name in candidatos:
                    if "flash" in name.lower():
                        return ver, name
                
                if candidatos:
                    return candidatos[0]
        except Exception as e:
            print(f"Error al verificar modelos en {api_version}: {e}")
            
    return None, None

def generar_texto_ia(pregunta):
    if not GEMINI_API_KEY:
        raise Exception("Falta la variable de entorno GEMINI_API_KEY en Render")

    api_version, model_name = obtener_modelo_y_version()
    
    if not model_name:
        raise Exception("No se encontró ningún modelo activo. Verifica que tu API Key en Render sea válida.")

    print(f"Modelo detectado automáticamente: {model_name} (Versión API: {api_version})")

    url = f"https://generativelanguage.googleapis.com/{api_version}/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_INSTRUCTION}\n\nPregunta: {pregunta}"}
                ]
            }
        ]
    }

    res = requests.post(url, json=payload, timeout=12)
    data = res.json()

    if res.status_code == 200:
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
    
    msg = data.get("error", {}).get("message", res.text)
    raise Exception(f"Error en {model_name}: {msg}")

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

        # Eliminar archivo anterior
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Crear audio de voz
        tts = gTTS(text=texto_respuesta, lang='es', slow=False)
        tts.save(AUDIO_FILE)

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
