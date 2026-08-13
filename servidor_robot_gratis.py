import os
import gc
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de clave API de Gemini desde Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def obtener_respuesta_gemini(prompt):
    """
    Consulta directa a modelos ligeros y oficiales sin sobrecargar la memoria.
    """
    modelos_ligeros = ['gemini-1.5-flash', 'gemini-1.5-pro']
    
    for nombre in modelos_ligeros:
        try:
            print(f"Consultando modelo ligero: {nombre}")
            model = genai.GenerativeModel(nombre)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"No se pudo usar {nombre}: {e}")
            continue

    raise Exception("Ningún modelo ligero respondió.")

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

        prompt = f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        
        # Generar texto con la IA
        texto_respuesta = obtener_respuesta_gemini(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Generar audio MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        # Liberar memoria RAM del servidor de forma inmediata
        gc.collect()

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        
        # Audio de respaldo
        tts = gTTS(text="Ocurrió un error de memoria o conexión en el servidor.", lang='es')
        tts.save("respuesta.mp3")
        gc.collect()
        
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def obtener_audio():
    if os.path.exists("respuesta.mp3"):
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
    return "Archivo de audio no encontrado", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

