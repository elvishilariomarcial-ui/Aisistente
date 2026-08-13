from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import os

app = Flask(__name__)

# 🔑 Tu clave de API de Gemini
API_KEY = "AQ.Ab8RN6IUIayie6NOarj0g3dwrUEBzDplLZGKmQ2NS91uxtV4Ew"
genai.configure(api_key=API_KEY)

def obtener_modelo_activo():
    """Busca un modelo de Gemini válido y disponible en la API"""
    # Lista de nombres comunes actualizados
    modelos_candidatos = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro'
    ]
    
    for nombre_modelo in modelos_candidatos:
        try:
            m = genai.GenerativeModel(nombre_modelo)
            return m
        except Exception:
            continue

    # Si ninguno de la lista funciona, consulta directamente a la API de Google
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                return genai.GenerativeModel(m.name)
    except Exception as e:
        print(f"Error listando modelos: {e}")
        
    return genai.GenerativeModel('gemini-2.5-flash')

@app.route('/asistente', methods=['GET', 'POST'])
def asistente():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        pregunta = data.get("pregunta", "Hola")
        
        try:
            # 1. Obtener modelo funcional
            model = obtener_modelo_activo()
            prompt = f"Responde en menos de 20 palabras de forma clara y directa: {pregunta}"
            
            response = model.generate_content(prompt)
            respuesta_texto = response.text
            print(f"Respuesta de IA: {respuesta_texto}")
            
        except Exception as e:
            print(f"Error al generar con Gemini: {e}")
            respuesta_texto = "Hola, he recibido tu mensaje correctamente."
        
        # 2. Generar el archivo MP3 con la voz
        tts = gTTS(text=respuesta_texto, lang='es')
        tts.save("respuesta.mp3")
        
        return send_file("respuesta.mp3", mimetype="audio/mpeg")
        
    elif request.method == 'GET':
        if os.path.exists("respuesta.mp3"):
            return send_file("respuesta.mp3", mimetype="audio/mpeg")
        return "No hay audio generado aún", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

