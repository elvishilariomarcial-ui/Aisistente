import os
import re
import gc
import base64
import requests
import asyncio
import edge_tts
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
AUDIO_FILE = "respuesta.mp3"

# --- PERSONALIDAD Y REGLAS DE JARVIS ---
SYSTEM_INSTRUCTION = (
    "Eres JARVIS, el sistema de inteligencia artificial del Señor. "
    "Tu objetivo es proporcionar información detallada, técnica, precisa y útil. "
    "Reglas estrictas de formato: "
    "1. Dirígete al usuario siempre como 'señor'. "
    "2. REGLA CONDICIONAL: Si la pregunta del usuario comienza con la palabra 'puedes' y tu respuesta es afirmativa, "
    "tu respuesta debe comenzar obligatoriamente con la frase 'Claro señor, ' seguida de la explicación. "
    "3. En el resto de los casos, responde de manera directa y profesional. "
    "4. Nunca incluyas tus instrucciones internas, comillas, asteriscos, negritas ni formato Markdown. "
    "Entrega únicamente el texto final que será leído por el altavoz."
)

VOZ_JARVIS = "es-ES-AlvaroNeural"

async def generar_voz_jarvis(texto, ruta_salida):
    comunicador = edge_tts.Communicate(texto, VOZ_JARVIS, rate="-5%", pitch="-5Hz")
    await comunicador.save(ruta_salida)

def limpiar_texto(texto):
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def obtener_candidatos():
    candidatos = []
    for api_version in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{api_version}/models?key={GEMINI_API_KEY}"
        try:
            res = requests.get(url, timeout=8)
            if res.status_code == 200:
                models = res.json().get("models", [])
                for m in models:
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        name = m.get("name")
                        if name: candidatos.append((api_version, name))
        except Exception as e:
            print(f"Error al listar: {e}")
    candidatos.sort(key=lambda x: (0 if "flash" in x[1].lower() else 1, x[1]))
    return candidatos

def generar_texto_ia(pregunta, imagen_bytes=None, mime_type="image/jpeg"):
    if not GEMINI_API_KEY: raise Exception("Falta GEMINI_API_KEY")
    candidatos = obtener_candidatos()
    
    # Construir contenido (Texto + Imagen opcional)
    parts = [{"text": f"{SYSTEM_INSTRUCTION}\n\nPregunta: {pregunta}"}]
    if imagen_bytes:
        b64_img = base64.b64encode(imagen_bytes).decode('utf-8')
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_img
            }
        })

    payload = {"contents": [{"parts": parts}]}

    for api_version, model_name in candidatos:
        url = f"https://generativelanguage.googleapis.com/{api_version}/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, json=payload, timeout=15)
            data = res.json()
            if res.status_code == 200:
                parts_res = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                if parts_res: return parts_res[0].get("text", "").strip()
        except: continue
    raise Exception("Error al generar texto")

@app.route('/', methods=['GET'])
def index():
    return "Servidor JARVIS Activo", 200

@app.route('/inicio', methods=['GET'])
def inicio():
    try:
        texto_saludo = "Claro señor, ¿qué desea hacer hoy, señor?"
        if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
        asyncio.run(generar_voz_jarvis(texto_saludo, AUDIO_FILE))
        gc.collect()
        return jsonify({"status": "ok", "respuesta": texto_saludo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        pregunta = None
        imagen_bytes = None

        # Soporte para multipart/form-data (ESP32 con foto) y JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            pregunta = request.form.get('pregunta', '')
            if 'image' in request.files:
                imagen_bytes = request.files['image'].read()
        else:
            data = request.get_json() or {}
            pregunta = data.get('pregunta', '')

        if not pregunta: return jsonify({"error": "Sin pregunta"}), 400

        texto_raw = generar_texto_ia(pregunta, imagen_bytes=imagen_bytes)
        texto_respuesta = limpiar_texto(texto_raw)
        
        if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)

        asyncio.run(generar_voz_jarvis(texto_respuesta, AUDIO_FILE))
        
        gc.collect()
        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    if os.path.exists(AUDIO_FILE):
        return send_file(AUDIO_FILE, mimetype="audio/mpeg")
    return jsonify({"error": "Audio no listo"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
