
import os
import io
import wave
import json
import zipfile
import requests as req_lib
from flask import Flask, request, send_file
from google import genai
from gtts import gTTS
from vosk import Model, KaldiRecognizer

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_CLAVE_GEMINI_AQUI")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

VOSK_MODEL_PATH = "model"
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
VOSK_ZIP_NAME = "vosk-model-small-es-0.42"

def descargar_modelo_si_falta():
    if os.path.isdir(VOSK_MODEL_PATH):
        print("Modelo Vosk ya existe, no se descarga de nuevo.")
        return

    print("Descargando modelo de Vosk en español (una sola vez)...")
    respuesta = req_lib.get(VOSK_MODEL_URL, stream=True)
    respuesta.raise_for_status()

    zip_path = "modelo_temp.zip"
    with open(zip_path, "wb") as f:
        for chunk in respuesta.iter_content(chunk_size=8192):
            f.write(chunk)

    print("Descomprimiendo modelo...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(".")

    os.rename(VOSK_ZIP_NAME, VOSK_MODEL_PATH)
    os.remove(zip_path)
    print("Modelo Vosk listo.")

descargar_modelo_si_falta()
vosk_model = Model(VOSK_MODEL_PATH)

SYSTEM_PROMPT = """Eres un robot asistente amigable y util, hecho con un ESP32.
Respondes de forma breve y clara, en 1-3 oraciones, ya que tus respuestas
se convierten a audio. Hablas en español de forma natural y cercana."""


@app.route("/", methods=["GET"])
def home():
    return "Servidor del robot asistente esta funcionando (version gratuita)."


@app.route("/asistente", methods=["POST"])
def procesar_audio():
    try:
        audio_bytes = request.data
        if not audio_bytes:
            return {"error": "No se recibio audio"}, 400

        texto_usuario = voz_a_texto(audio_bytes)
        print(f"Usuario dijo: {texto_usuario}")

        if not texto_usuario or texto_usuario.strip() == "":
            return {"error": "No se pudo transcribir el audio"}, 400

        respuesta_texto = generar_respuesta(texto_usuario)
        print(f"Gemini respondio: {respuesta_texto}")

        audio_respuesta = texto_a_voz(respuesta_texto)

        return send_file(
            io.BytesIO(audio_respuesta),
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}, 500


def voz_a_texto(audio_bytes):
    wf = wave.open(io.BytesIO(audio_bytes), "rb")
    recognizer = KaldiRecognizer(vosk_model, wf.getframerate())
    recognizer.SetWords(True)

    texto_completo = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            resultado = json.loads(recognizer.Result())
            texto_completo += resultado.get("text", "") + " "

    resultado_final = json.loads(recognizer.FinalResult())
    texto_completo += resultado_final.get("text", "")

    return texto_completo.strip()


def generar_respuesta(texto_usuario):
    prompt_completo = f"{SYSTEM_PROMPT}\n\nUsuario: {texto_usuario}"
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_completo
    )
    return response.text


def texto_a_voz(texto):
    tts = gTTS(text=texto, lang="es")
    buffer_audio = io.BytesIO()
    tts.write_to_fp(buffer_audio)
    buffer_audio.seek(0)
    return buffer_audio.read()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
