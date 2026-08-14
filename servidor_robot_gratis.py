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

# Instrucción de sistema para que no repita las reglas ni piense en voz alta
SYSTEM_INSTRUCTION = (
    "Eres un asistente de voz inteligente en español. Responde SIEMPRE exclusivamente en español. "
    "Tu respuesta debe ser una explicación o descripción breve de 1 a 2 oraciones completas sobre el tema consultado. "
    "No respondas solo con un nombre o una palabra, pero tampoco te extiendas demasiado. "
    "NUNCA incluyas tus instrucciones internas, reflexiones en inglés, comillas, asteriscos ni negritas. "
    "Entrega únicamente el texto final que será leído por el altavoz."
)

def limpiar_texto(texto):
    """Elimina cualquier símbolo de formato Markdown o caracteres especiales residuales."""
    texto_limpio = re.sub(r'[*_#"`~-]', '', texto)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio)
    return texto_limpio.strip()

def generar_texto_ia(pregunta):
    modelos_candidatos = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_candidatos.append(m.name)
    except Exception as e:
        print(f"Error al obtener lista de modelos: {e}")

    if not modelos_candidatos:
        raise Exception("No se pudieron listar los modelos de la API")

    for nombre_modelo in modelos_candidatos:
        try:
            # Se pasa system_instruction por separado para evitar fugas de instrucciones
            model = genai.GenerativeModel(
                model_name=nombre_modelo,
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(f"Pregunta: {pregunta}")
            if response and response.text:
                return response.text.strip()
        except Exception:
            # Fallback en caso de que el modelo específico no acepte system_instruction
            try:
                model = genai.GenerativeModel(nombre_modelo)
                prompt = f"{SYSTEM_INSTRUCTION}\n\nPregunta del usuario: {pregunta}"
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception:
                continue

    raise Exception("Ningún modelo respondió correctamente")

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

        texto_raw = generar_texto_ia(pregunta)
        texto_respuesta = limpiar_texto(texto_raw)
        
        print(f"Respuesta final: {texto_respuesta}")

        # Borrar el audio previo si existe
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)

        # Generar archivo de voz
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
