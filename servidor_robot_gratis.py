from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import os

app = Flask(__name__)

# 🔑 Tu clave de API de Gemini configurada
API_KEY = "AQ.Ab8RN6IUIayie6NOarj0g3dwrUEBzDplLZGKmQ2NS91uxtV4Ew"
genai.configure(api_key=API_KEY)

# Modelo ligero y rápido ideal para respuestas en tiempo real
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        pregunta = data.get("pregunta", "Hola")
        
        try:
            # 1. Consultar a la IA Gemini
            prompt = f"Responde en menos de 20 palabras de forma clara y directa: {pregunta}"
            response = model.generate_content(prompt)
            respuesta_texto = response.text
        except Exception as e:
            print(f"Error en Gemini: {e}")
            respuesta_texto = "Lo siento, tuve un problema al procesar la respuesta."
        
        # 2. Convertir la respuesta a voz (MP3)
        tts = gTTS(text=respuesta_texto, lang='es')
        tts.save("respuesta.mp3")
        
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
        
    elif request.method == 'GET':
        # Entrega el archivo de audio para reproducción
        if os.path.exists("respuesta.mp3"):
            return send_file("respuesta.mp3", mimetype="audio/mpeg")
        return "No hay audio generado aún", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
