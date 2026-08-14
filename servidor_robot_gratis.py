import os
import gc
import requests
from flask import Flask, request, jsonify, Response
from gtts import gTTS

app = Flask(__name__)

# Clave de API de Gemini (usa la variable de entorno o tu clave directa)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IUIayie6NOarj0g3dwrUEBzDplLZGKmQ2NS91uxtV4Ew")

# Ruta absoluta garantizada para almacenar el archivo MP3
AUDIO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "respuesta.mp3")

def consultar_gemini_dinamico(prompt):
    if not GEMINI_API_KEY:
        raise Exception("No se encontró ninguna GEMINI_API_KEY válida.")

    # 1. Obtener automáticamente los modelos disponibles en tu cuenta de Google
    url_listado = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    modelos_disponibles = []
    
    try:
        res_list = requests.get(url_listado, timeout=10)
        if res_list.status_code == 200:
            data_list = res_list.json()
            for m in data_list.get("models", []):
                # Filtrar solo modelos que soporten generación de texto
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    modelos_disponibles.append(m["name"])
    except Exception as e:
        print(f"Error al listar modelos: {e}")

    # Fallback si falla el listado automático
    if not modelos_disponibles:
        modelos_disponibles = [
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
            "models/gemini-2.0-flash"
        ]

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    ultimo_error = ""

    # 2. Probar los modelos detectados hasta que uno responda con éxito
    for nombre_modelo in modelos_disponibles:
        if not nombre_modelo.startswith("models/"):
            nombre_modelo = f"models/{nombre_modelo}"

        url = f"https://generativelanguage.googleapis.com/v1beta/{nombre_modelo}:generateContent?key={GEMINI_API_KEY}"
        try:
            print(f"Consultando modelo: {nombre_modelo}...")
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            data = res.json()

            if res.status_code == 200:
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        print(f"¡Éxito con el modelo {nombre_modelo}!")
                        return parts[0]["text"]
            else:
                ultimo_error = data.get("error", {}).get("message", res.text)
        except Exception as e:
            ultimo_error = str(e)

    raise Exception(f"Ningún modelo respondió. Último error: {ultimo_error}")

@app.route('/', methods=['GET'])
def home():
    return "Servidor del Asistente Activo y Listo", 200

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        data = request.get_json(silent=True) or {}
        pregunta = data.get('pregunta', '')

        if not pregunta:
            return jsonify({"error": "No se recibió ninguna pregunta"}), 400

        print(f"Pregunta recibida: {pregunta}")

        # Pedir respuesta breve para no saturar la memoria del ESP32
        prompt = f"Responde de forma breve y concisa (máximo 2 oraciones) para ser leída en voz alta: {pregunta}"
        
        texto_respuesta = consultar_gemini_dinamico(prompt)
        print(f"Respuesta IA: {texto_respuesta}")

        # Limpiar audio anterior si existía
        if os.path.exists(AUDIO_PATH):
            os.remove(AUDIO_PATH)

        # Generar archivo de voz MP3 con gTTS
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
        try:
            # Leer el archivo binario completo
            with open(AUDIO_PATH, "rb") as f:
                contenido_bytes = f.read()
            
            tamano = len(contenido_bytes)
            print(f"Enviando {tamano} bytes de audio al ESP32...")

            # Respuesta binaria limpia para reproductores de hardware como ESP32
            return Response(
                contenido_bytes,
                status=200,
                mimetype="audio/mpeg",
                headers={
                    "Content-Type": "audio/mpeg",
                    "Content-Length": str(tamano),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        except Exception as e:
            print(f"Error al leer el binario de audio: {e}")
            return "Error al procesar el audio", 500

    print("Error: Archivo respuesta.mp3 no encontrado")
    return "Archivo de audio no encontrado", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
