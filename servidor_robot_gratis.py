from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import os

app = Flask(__name__)

# 🔑 Tu clave de API de Gemini
API_KEY = "AQ.Ab8RN6IUIayie6NOarj0g3dwrUEBzDplLZGKmQ2NS91uxtV4Ew"
genai.configure(api_key=API_KEY)

# Lista de modelos oficiales a probar en orden
MODELOS_ESTABLES = [
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-2.0-flash'
]

def generar_respuesta_ia(prompt):
    """Intenta generar respuesta probando los modelos disponibles"""
    for nombre_modelo in MODELOS_ESTABLES:
        try:
            print(f"Probando con modelo: {nombre_modelo}")
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            if response and response.text:
                print(f"¡Éxito con {nombre_modelo}!")
                return response.text
        except Exception as e:
            print(f"No disponible ({nombre_modelo}): {e}")
            continue

    # Si por alguna razón la API no responde, envía un mensaje de respaldo
    return "Hola, he recibido tu pregunta correctamente."

@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        pregunta = data.get("pregunta", "Hola")
        
        # 1. Consultar a Gemini
        prompt = f"Responde en menos de 20 palabras de forma clara y directa: {pregunta}"
        respuesta_texto = generar_respuesta_ia(prompt)
        print(f"Texto a convertir en voz: {respuesta_texto}")
        
        # 2. Generar audio MP3
        tts = gTTS(text=respuesta_texto, lang='es')
        tts.save("respuesta.mp3")
        
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
        
    elif request.method == 'GET':
        if os.path.exists("respuesta.mp3"):
            return send_file("respuesta.mp3", mimetype="audio/mpeg")
        return "No hay audio generado aún", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
