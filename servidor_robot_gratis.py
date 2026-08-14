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

def obtener_modelo_activo():
    """Busca automáticamente un modelo funcional en la API de Google."""
    try:
        modelos = genai.list_models()
        modelos_compatibles = []
        
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods:
                modelos_compatibles.append(m.name)
        
        # Priorizar modelos 'flash' por ser más rápidos para respuestas cortas
        for nombre_modelo in modelos_compatibles:
            if 'flash' in nombre_modelo.lower():
                print(f"Modelo seleccionado automáticamente: {nombre_modelo}")
                return nombre_modelo
        
        # Si no hay 'flash', usa el primer modelo disponible
        if modelos_compatibles:
            print(f"Modelo fallback seleccionado: {modelos_compatibles[0]}")
            return modelos_compatibles[0]

    except Exception as e:
        print(f"Error al listar modelos: {str(e)}")
    
    # Nombre por defecto si la consulta de lista falla
    return "gemini-1.5-flash-latest"

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

        # Obtener un modelo válido y activo
        nombre_modelo = obtener_modelo_activo()
        model = genai.GenerativeModel(nombre_modelo)
        
        # Generar texto de respuesta
        response = model.generate_content(f"Responde de forma concisa en una sola frase: {pregunta}")
        texto_respuesta = response.text.strip()
        
        print(f"Respuesta IA: {texto_respuesta}")

        # Borrar el audio previo si existe para evitar conflictos de escritura
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
