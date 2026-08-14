import os
import re
import gc
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de la API Key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

AUDIO_FILE = "respuesta.mp3"

# Modelos recomendados ordenados por prioridad y rapidez
MODELOS_PREFERIDOS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro"
]

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
    """Intenta generar respuesta probando únicamente una lista corta de modelos rápidos."""
    ultimo_error = ""
    for nombre_modelo in MODELOS_PREFERIDOS:
        try:
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(f"Pregunta: {pregunta}")
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            ultimo_error = str(e)
            continue
            
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

        # Limpieza de archivo previo
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Generación de voz
        tts = gTTS(text=texto_respuesta, lang='es', slow=False)
        tts.save(AUDIO_FILE)

        # Forzar la recolección de basura para liberar RAM en Render
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
        return jsonify({"error": "Archivo no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
