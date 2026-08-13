from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import os

app = Flask(__name__)

@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    if request.method == 'POST':
        # 1. Recibe la pregunta de la ESP32
        data = request.get_json(silent=True) or {}
        pregunta = data.get("pregunta", "")
        
        # -------------------------------------------------------------
        # AQUÍ VA TU LÓGICA DE IA (OpenAI, Gemini, etc.)
        # Ejemplo:
        respuesta_texto = f"Recibí tu pregunta: {pregunta}"
        # -------------------------------------------------------------
        
        # 2. Genera el audio en MP3
        tts = gTTS(text=respuesta_texto, lang='es')
        tts.save("respuesta.mp3")
        
        # Devuelve confirmación
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
        
    elif request.method == 'GET':
        # 3. La ESP32 entra aquí con GET para reproducir el MP3
        if os.path.exists("respuesta.mp3"):
            return send_file("respuesta.mp3", mimetype="audio/mpeg")
        else:
            return "No hay audio generado aún", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
