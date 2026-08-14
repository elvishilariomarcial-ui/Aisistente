import os
import re
from flask import Flask, request, jsonify, send_file
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de la API Key desde las variables de entorno de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

AUDIO_FILE = "respuesta.mp3"

def limpiar_texto(texto):
    """
    Elimina comillas, asteriscos, guiones y símbolos de formato 
    para que la voz lea únicamente la frase limpia.
    """
    # Eliminar asteriscos, comillas, almohadillas, guiones y tildes de formato
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    # Reemplazar múltiples espacios o saltos de línea por un solo espacio
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def generar_texto_ia(prompt):
    modelos_candidatos = []
    
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_candidatos.append(m.name)
    except Exception as e:
        print(f"Error al obtener lista de modelos: {e}")

    if not modelos_candidatos:
        raise Exception("No se pudieron listar los modelos de la API")

    ultimo_error = ""
    
    for nombre_modelo in modelos_candidatos:
        try:
            print(f"Probando modelo: {nombre_modelo}")
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            
            if response and response.text:
                print(f"¡Respuesta exitosa recibida de {nombre_modelo}!")
                return response.text.strip()
                
        except Exception as e:
            print(f"Fallo en {nombre_modelo}: {str(e)}")
            ultimo_error = str(e)
            continue

    raise Exception(f"Ningún modelo de Gemini respondió. Último mensaje: {ultimo_error}")

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

        # Prompt que exige texto plano directo
        prompt = f"Responde de forma directa y concisa en una sola frase, usando únicamente texto plano sin asteriscos, sin comillas y sin negritas: {pregunta}"
        
        texto_raw = generar_texto_ia(prompt)
        
        # Filtro de seguridad para limpiar cualquier símbolo restante
        texto_respuesta = limpiar_texto(texto_raw)
        
        print(f"Respuesta limpia: {texto_respuesta}")

        # Borrar el audio previo si existe
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Generar archivo MP3 con el texto limpio
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
