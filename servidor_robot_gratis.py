import os
import re
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de la API Key desde las variables de entorno de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

AUDIO_FILE = "respuesta.mp3"

def limpiar_texto(texto):
    # Eliminar asteriscos, comillas, almohadillas, guiones y tildes de formato
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    # Reemplazar múltiples espacios por uno solo
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def generar_texto_ia(prompt):
    modelos_candidatos = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_candidatos.append(m.name)
    except Exception as e:
        print(f"Error al obtener lista de modelos: {e}")

    if not modelos_candidatos:
        raise Exception("No se pudieron listar los modelos")

    for nombre_modelo in modelos_candidatos:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            # Enviar el prompt
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            continue
    raise Exception("Ningún modelo respondió correctamente")

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json()
        pregunta = data.get('pregunta', '')

        # INSTRUCCIÓN REFORZADA: Se añade "Responde SIEMPRE en español"
        prompt = (f"Responde SIEMPRE en español, de forma directa, breve y concisa. "
                  f"No incluyas asteriscos, comillas, negritas ni otros formatos especiales. "
                  f"Solo el texto de la respuesta. Pregunta: {pregunta}")
        
        texto_raw = generar_texto_ia(prompt)
        texto_respuesta = limpiar_texto(texto_raw)
        
        print(f"Respuesta final en español: {texto_respuesta}")

        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        tts = gTTS(text=texto_respuesta, lang='es', slow=False)
        tts.save(AUDIO_FILE)

        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error interno: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    try:
        return send_file(AUDIO_FILE, mimetype="audio/mpeg")
    except:
        return jsonify({"error": "No encontrado"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
