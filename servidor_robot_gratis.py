import os
import re
import gc
import requests
import asyncio
import traceback
import edge_tts
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if GROQ_API_KEY:
    print(f"DEBUG: GROQ_API_KEY detectada correctamente (longitud: {len(GROQ_API_KEY)})")
else:
    print("DEBUG: ¡ATENCIÓN! GROQ_API_KEY no está configurada o está vacía en Render.")

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
    "el correcto procesamiento del sintetizador de voz. Si la respuesta es corta, extiéndela cortésmente. "
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

def generar_texto_ia(pregunta, imagen_base64=None):
    if not GROQ_API_KEY: 
        raise Exception("Falta la clave de API de Groq en las variables de entorno")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Modelos actualizados y vigentes en Groq
    if imagen_base64 and len(imagen_base64) > 100:
        modelos_disponibles = [
            "llama-3.2-11b-vision-preview",
            "llama-3.2-90b-vision-preview",
            "openai/gpt-oss-120b"
        ]
        user_content = [
            {"type": "text", "text": pregunta},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen_base64}"}}
        ]
    else:
        modelos_disponibles = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ]
        user_content = pregunta

    for modelo in modelos_disponibles:
        payload = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.7
        }
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                print(f"Modelo {modelo} falló con código {res.status_code}: {res.text[:100]}, probando siguiente...")
        except Exception as e:
            print(f"Error al intentar con el modelo {modelo}: {e}, probando siguiente...")
            continue
            
    raise Exception("Error al generar texto: Ninguno de los modelos disponibles respondió correctamente.")

@app.route('/', methods=['GET'])
def index():
    return "Servidor JARVIS Activo (Groq)", 200

@app.route('/preguntar', methods=['POST'])
def preguntar():
    try:
        pregunta = request.form.get('pregunta', '')
        imagen = request.form.get('imagen', '')
        
        if not pregunta:
            return jsonify({"error": "Petición vacía"}), 400

        texto_raw = generar_texto_ia(pregunta, imagen)
        texto_respuesta = limpiar_texto(texto_raw)
        
        if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
        asyncio.run(generar_voz_jarvis(texto_respuesta, AUDIO_FILE))
        gc.collect()
        
        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        texto_pregunta = ""
        if request.is_json:
            data = request.get_json() or {}
            texto_pregunta = data.get('pregunta', '')

        if not texto_pregunta: 
            return jsonify({"error": "Petición vacía"}), 400

        texto_raw = generar_texto_ia(texto_pregunta)
        texto_respuesta = limpiar_texto(texto_raw)
        
        if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
        asyncio.run(generar_voz_jarvis(texto_respuesta, AUDIO_FILE))
        gc.collect()
        
        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    if os.path.exists(AUDIO_FILE):
        file_size = os.path.getsize(AUDIO_FILE)
        response = send_file(AUDIO_FILE, mimetype="audio/mpeg")
        response.headers["Content-Length"] = str(file_size)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    return jsonify({"error": "Audio no listo"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
