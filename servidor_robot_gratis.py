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

def obtener_modelo_activo():
    """Selecciona automáticamente el modelo disponible en tu cuenta."""
    try:
        modelos = list(genai.list_models())
        # Buscar primero un modelo de la familia 'flash' disponible
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name:
                    print(f"Usando modelo: {m.name}")
                    return genai.GenerativeModel(m.name)
        # Si no encuentra 'flash', usa el primer modelo disponible
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods:
                print(f"Usando modelo: {m.name}")
                return genai.GenerativeModel(m.name)
    except Exception as e:
        print(f"Error detectando modelos: {e}")
    
    # Modelo predeterminado de respaldo
    return genai.GenerativeModel('models/gemini-1.5-flash')

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

        # Obtener modelo dinámico
        model = obtener_modelo_activo()

        # Generar respuesta con la IA
        response = model.generate_content(
            f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        )
        texto_respuesta = response.text
        print(f"Respuesta IA: {texto_respuesta}")

        # Convertir texto a archivo de audio MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        # Audio de respaldo para evitar fallos en la ESP32
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
