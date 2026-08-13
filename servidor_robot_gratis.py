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

def generar_respuesta_ia(prompt):
    """
    Prueba dinámicamente varios modelos de Gemini hasta encontrar
    uno activo y compatible con la clave de API.
    """
    modelos_a_probar = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-2.0-flash',
        'gemini-1.5-flash-8b',
        'models/gemini-1.5-flash',
        'models/gemini-1.5-pro'
    ]

    # Agregar otros modelos listados por la API
    try:
        modelos_disponibles = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        for m_name in modelos_disponibles:
            if m_name not in modelos_a_probar:
                modelos_a_probar.append(m_name)
    except Exception as e:
        print(f"No se pudo consultar la lista de modelos: {e}")

    # Probar cada modelo hasta que uno responda
    ultimo_error = None
    for nombre_modelo in modelos_a_probar:
        try:
            print(f"Probando con modelo: {nombre_modelo}...")
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            if response and response.text:
                print(f"¡Modelo funcional encontrado!: {nombre_modelo}")
                return response.text
        except Exception as e:
            print(f"Modelo {nombre_modelo} no disponible: {e}")
            ultimo_error = e

    raise Exception(f"Ningún modelo estuvo disponible. Último error: {ultimo_error}")

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
        
        # Generar respuesta probando modelos activos
        texto_respuesta = generar_respuesta_ia(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Convertir texto a archivo MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save("respuesta.mp3")

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando la solicitud: {e}")
        # Audio de respaldo para evitar fallos en el microcontrolador
        mensaje_error = "Ocurrió un error al procesar tu pregunta con la inteligencia artificial."
        tts = gTTS(text=mensaje_error, lang='es')
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
