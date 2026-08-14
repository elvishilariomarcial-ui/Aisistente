import os
import gc
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Ruta absoluta garantizada para almacenar el archivo MP3
AUDIO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "respuesta.mp3")

def consultar_gemini_dinamico(prompt):
    if not GEMINI_API_KEY:
        raise Exception("No se encontró GEMINI_API_KEY en las configuraciones de Render.")

    url_listado = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    modelos_disponibles = []
    
    try:
        res_list = requests.get(url_listado, timeout=10)
        if res_list.status_code == 200:
            data_list = res_list.json()
            for m in data_list.get("models", []):
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    modelos_disponibles.append(m["name"])
    except Exception as e:
        print(f"Error al listar modelos: {e}")

    if not modelos_disponibles:
        modelos_disponibles = ["models/gemini-1.5-flash", "models/gemini-1.5-pro"]

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    ultimo_error = ""

    for nombre_modelo in modelos_disponibles:
        if not nombre_modelo.startswith("models/"):
            nombre_modelo = f"models/{nombre_modelo}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{nombre_modelo}:generateContent?key={GEMINI_API_KEY}"
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            data = res.json()

            if res.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            else:
                ultimo_error = data.get("error", {}).get("message", res.text)
        except Exception as e:
            ultimo_error = str(e)

    raise Exception(f"Ningún modelo respondió. Último error: {ultimo_error}")

@app.route('/', methods=['GET'])
def home():
    return "Servidor del Asistente Activo", 200

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json(silent=True) or {}
        pregunta = data.get('pregunta', '')

        if not pregunta:
            return jsonify({"error": "No se recibió ninguna pregunta"}), 400

        print(f"Pregunta recibida: {pregunta}")

        prompt = f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        
        texto_respuesta = consultar_gemini_dinamico(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Eliminar versión anterior si existe
        if os.path.exists(AUDIO_PATH):
            os.remove(AUDIO_PATH)

        # Generar nuevo audio MP3
        tts = gTTS(text=texto_respuesta, lang='es')
        tts.save(AUDIO_PATH)

        tamano = os.path.getsize(AUDIO_PATH) if os.path.exists(AUDIO_PATH) else 0
        print(f"Audio generado con éxito. Tamaño: {tamano} bytes")

        gc.collect()

        return jsonify({"respuesta": texto_respuesta}), 200

    except Exception as e:
        print(f"Error procesando solicitud: {e}")
        
        if os.path.exists(AUDIO_PATH):
            os.remove(AUDIO_PATH)
            
        tts = gTTS(text="Ocurrió un error al procesar tu solicitud.", lang='es')
        tts.save(AUDIO_PATH)
        gc.collect()
        
        return jsonify({"error": str(e)}), 500

@app.route('/audio', methods=['GET'])
def obtener_audio():
    if os.path.exists(AUDIO_PATH):
        tamano_archivo = os.path.getsize(AUDIO_PATH)
        print(f"Enviando audio al ESP32 ({tamano_archivo} bytes)...")
        
        response = send_file(
            AUDIO_PATH,
            mimetype="audio/mpeg",
            as_attachment=False
        )
        
        # Encabezados necesarios para reproductores de hardware como ESP32
        response.headers["Content-Length"] = str(tamano_archivo)
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    print("Error: Archivo respuesta.mp3 no encontrado")
    return "Archivo de audio no encontrado", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
