import os
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE LA CLAVE API DESDE RENDER
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Inicializar el modelo recomendado
model = genai.GenerativeModel('gemini-1.5-flash')

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

        # Generar respuesta corta con IA
        response = model.generate_content(
            f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        )
        texto_respuesta = response.text
        print(f"Respuesta IA: {texto_respuesta}")

        # Convertir texto a voz MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        # Audio de respaldo en caso de fallo
        tts = gTTS(text="Ocurrió un error al procesar tu pregunta.", lang='es')
        tts.save("respuesta.mp3")
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def obtener_audio():
    if os.path.exists("respuesta.mp3"):
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
    return "Archivo de audio no encontrado", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
