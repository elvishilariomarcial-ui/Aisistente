import os
import io
from flask import Flask, request, send_file
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr

app = Flask(__name__)

# Configuración de la API Key de Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_API_KEY_AQUI")
genai.configure(api_key=GEMINI_API_KEY)

def obtener_modelo_activo():
    """Prueba en vivo los modelos de la lista hasta encontrar uno activo y funcionando."""
    try:
        modelos = genai.list_models()
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods:
                try:
                    nombre = m.name
                    # Creamos e intentamos una respuesta mínima para validar
                    m_test = genai.GenerativeModel(nombre)
                    m_test.generate_content("hola")
                    print(f"[SERVIDOR] ¡Modelo verificado exitosamente!: {nombre}")
                    return m_test
                except Exception as e:
                    print(f"[SERVIDOR] El modelo {m.name} no está disponible ({e}), probando el siguiente...")
                    continue
    except Exception as e:
        print(f"[SERVIDOR] Error al listar modelos: {e}")
    
    # Modelo respaldo por si acaso
    return genai.GenerativeModel('gemini-2.0-flash')

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        pregunta_texto = ""

        # ------------------------------------------------------------------
        # CASO 1: Si envías TEXTO desde el Celular o ESP32 (JSON)
        # ------------------------------------------------------------------
        if request.is_json:
            data = request.get_json()
            pregunta_texto = data.get("pregunta", "")
            print(f"[SERVIDOR] Texto recibido: {pregunta_texto}")

        # ------------------------------------------------------------------
        # CASO 2: Si envías AUDIO desde un Micrófono (RAW / WAV)
        # ------------------------------------------------------------------
        else:
            audio_bytes = request.data
            if not audio_bytes:
                return {"error": "No se recibieron datos de audio ni texto"}, 400

            print("[SERVIDOR] Audio recibido. Procesando voz a texto...")
            recognizer = sr.Recognizer()
            audio_file = io.BytesIO(audio_bytes)
            
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
                pregunta_texto = recognizer.recognize_google(audio_data, language="es-ES")
            print(f"[SERVIDOR] Audio reconocido como: {pregunta_texto}")

        if not pregunta_texto:
            return {"error": "No se pudo obtener una pregunta valida"}, 400

        # ------------------------------------------------------------------
        # PROCESAR PREGUNTA CON GEMINI IA
        # ------------------------------------------------------------------
        model = obtener_modelo_activo()
        response = model.generate_content(pregunta_texto)
        texto_respuesta = response.text
        print(f"[SERVIDOR] Respuesta IA: {texto_respuesta}")

        # ------------------------------------------------------------------
        # CONVERTIR RESPUESTA DE LA IA A AUDIO MP3
        # ------------------------------------------------------------------
        tts = gTTS(text=texto_respuesta, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        # Retornar el archivo de voz MP3
        return send_file(fp, mimetype="audio/mpeg")

    except Exception as e:
        print(f"[ERROR]: {str(e)}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
