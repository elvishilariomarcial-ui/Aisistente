from flask import Flask, request, send_file, jsonify
import google.generativeai as genai
from gtts import gTTS
import os

app = Flask(__name__)

# 🔑 Tu clave de API de Gemini (debe empezar con AIzaSy...)
API_KEY = "TU_CLAVE_AQUI"
genai.configure(api_key=API_KEY)

@app.route('/asistente', methods=['POST'])
def asistente():
    data = request.get_json(silent=True) or {}
    pregunta = data.get("pregunta", "Hola")
    
    try:
        # Intentar responder con Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"Responde en menos de 20 palabras de forma clara: {pregunta}"
        response = model.generate_content(prompt)
        respuesta_texto = response.text
        print(f"Respuesta de IA: {respuesta_texto}")
    except Exception as e:
        print(f"Error Gemini: {e}")
        respuesta_texto = "Hola, he recibido tu mensaje correctamente."
    
    # Eliminar audio anterior si existe
    if os.path.exists("respuesta.mp3"):
        os.remove("respuesta.mp3")
        
    # Generar nuevo MP3
    tts = gTTS(text=respuesta_texto, lang='es')
    tts.save("respuesta.mp3")
    
    return jsonify({"status": "ok"})

@app.route('/audio', methods=['GET'])
def descargar_audio():
    if os.path.exists("respuesta.mp3"):
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
    return "No hay audio", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
