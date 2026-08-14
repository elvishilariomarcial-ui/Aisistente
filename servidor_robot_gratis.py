import os
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de la API Key desde las variables de entorno de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

AUDIO_FILE = "respuesta.mp3"

def generar_texto_ia(prompt):
    """
    Recorre la lista de modelos de Google y genera respuesta 
    con el primero que funcione correctamente.
    """
    modelos_candidatos = []
    
    try:
        # Obtener todos los modelos soportados
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_candidatos.append(m.name)
    except Exception as e:
        print(f"Error al obtener lista de modelos: {e}")

    if not modelos_candidatos:
        raise Exception("No se pudieron listar los modelos de la API")

    ultimo_error = ""
    
    # Probar modelo por modelo hasta tener éxito
    for nombre_modelo in modelos_candidatos:
        try:
            print(f"Probando modelo: {nombre_modelo}")
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            
            if response and response.text:
                print(f"¡Respuesta exitosa recibida de {nombre_modelo}!")
                return response.text.strip()
                
        except Exception as e:
            print(f"Fallo en {nombre_modelo}: {str(e)}")
            ultimo_error = str(e)
            continue

    raise Exception(f"Ningún modelo de Gemini respondió. Último mensaje: {ultimo_error}")

@app.route('/', methods=['GET'])
def index():
    return "Servidor Asistente IA Activo", 200

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json()
        pregunta = data.get('pregunta', '')

        if not pregunta:
            return jsonify({"error": "No se recibió ninguna pregunta"}), 400

        print(f"Pregunta recibida: {pregunta}")

        # Generar respuesta probando modelos dinámicamente
        prompt = f"Responde de forma concisa en una sola frase: {pregunta}"
        texto_respuesta = generar_texto_ia(prompt)
        
        print(f"Respuesta IA: {texto_respuesta}")

        # Borrar el audio previo si existe
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Generar nuevo archivo MP3
        tts = gTTS(text=texto_respuesta, lang='es', slow=False)
        tts.save(AUDIO_FILE)

        print("Audio generado con éxito.")
        return jsonify({"status": "ok", "respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error interno: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def audio():
    try:
        if os.path.exists(AUDIO_FILE):
            return send_file(AUDIO_FILE, mimetype="audio/mpeg")
        else:
            return jsonify({"error": "Archivo de audio no encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
