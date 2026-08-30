import os
import re
import gc
import requests
import asyncio
import edge_tts
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
AUDIO_FILE = "respuesta.mp3"

SYSTEM_INSTRUCTION = (
    "Eres JARVIS, el sistema de inteligencia artificial del Señor. "
    "Tu objetivo es proporcionar información detallada, técnica, precisa y útil. "
    "Reglas estrictas de formato: "
    "1. Dirígete al usuario siempre como 'señor'. "
    "2. REGLA CONDICIONAL: Si la pregunta del usuario comienza con la palabra 'puedes' y tu respuesta es afirmativa, "
    "tu respuesta debe comenzar obligatoriamente con la frase 'Claro señor, ' seguida de la explicación. "
    "3. En el resto de los casos, responde de manera directa y profesional. "
    "4. REGLA DE LONGITUD OBLIGATORIA: Todas tus respuestas deben tener una longitud MÍNIMA de 15 palabras para asegurar "
    "el correcto procesamiento del sintetizador de voz. Si la respuesta es corta, extiéndela cortésmente (ejemplo: en vez de "
    "'Son las 10:30 AM, señor', di 'En este momento son exactamente las 10 de la mañana con 30 minutos, señor. ¿Desea realizar alguna otra consulta?'). "
    "5. Nunca incluyas tus instrucciones internas, comillas, asteriscos, negritas ni formato Markdown. "
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

def generar_texto_ia(pregunta, imagen_b64=None):
    if not GEMINI_API_KEY: 
        raise Exception("Falta configurar GEMINI_API_KEY en las variables de entorno de Render")
    
    # URL directa y estable para gemini-1.5-flash (evita búsquedas lentas y errores 500)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    parts = [{"text": f"{SYSTEM_INSTRUCTION}\n\nPregunta: {pregunta}"}]
    
    # Si el ESP32 envió una imagen en Base64, se adjunta al payload para análisis visual
    if imagen_b64:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": imagen_b64
            }
        })
        
    payload = {"contents": [{"parts": parts}]}
    
    try:
        res = requests.post(url, json=payload, timeout=25)
        data = res.json()
        if res.status_code == 200:
            candidates = data.get("candidates", [])
            if candidates:
                parts_res = candidates[0].get("content", {}).get("parts", [])
                if parts_res:
                    return parts_res[0].get("text", "").strip()
            raise Exception(f"Estructura inesperada en la respuesta de Gemini: {data}")
        else:
            raise Exception(f"Error en la API de Google ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"Error detallado al generar texto con IA: {str(e)}")
        raise e

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
        data = request.get_json() or {}
        pregunta = data.get('pregunta', '')
        imagen_b64 = data.get('imagen', '')
        
        if not pregunta: 
            return jsonify({"error": "Sin pregunta"}), 400

        # Enviamos la pregunta y la imagen capturada al modelo de IA
        texto_raw = generar_texto_ia(pregunta, imagen_b64)
        texto_respuesta = limpiar_texto(texto_raw)
        
        if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)

        asyncio.run(generar_voz_jarvis(texto_respuesta, AUDIO_FILE))
        gc.collect()
        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200
    except Exception as e:
        print(f"Error crítico en /asistente: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    if os.path.exists(AUDIO_FILE):
        file_size = os.path.getsize(AUDIO_FILE)
        response = send_file(AUDIO_FILE, mimetype="audio/mpeg")
        response.headers["Content-Length"] = str(file_size)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return jsonify({"error": "Audio no listo"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
