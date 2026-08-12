import os
import io
from flask import Flask, request, send_file, render_template_string
import google.generativeai as genai
from gtts import gTTS
import speech_recognition as sr

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_API_KEY_AQUI")
genai.configure(api_key=GEMINI_API_KEY)

def obtener_modelo_activo():
    try:
        modelos = genai.list_models()
        for m in modelos:
            if 'generateContent' in m.supported_generation_methods:
                try:
                    nombre = m.name
                    m_test = genai.GenerativeModel(nombre)
                    m_test.generate_content("hola")
                    return m_test
                except Exception:
                    continue
    except Exception as e:
        print(f"[SERVIDOR] Error al listar modelos: {e}")
    return genai.GenerativeModel('gemini-2.0-flash')

# ------------------------------------------------------------------
# INTERFAZ WEB PARA EL CELULAR (MICRÓFONO Y TECLADO)
# ------------------------------------------------------------------
@app.route('/', methods=['GET'])
def pagina_inicio():
    html = '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Asistente Robot</title>
        <style>
            body { font-family: Arial, sans-serif; background: #121212; color: white; text-align: center; padding: 20px; }
            input { width: 85%; padding: 12px; font-size: 16px; border-radius: 8px; border: none; margin: 10px 0; }
            button { background: #007bff; color: white; border: none; padding: 15px 20px; font-size: 16px; border-radius: 8px; margin: 5px; cursor: pointer; }
            button:active { background: #0056b3; }
            #status { font-weight: bold; margin-top: 15px; color: #00ffcc; }
        </style>
    </head>
    <body>
        <h2>🤖 Asistente IA Celular</h2>
        <input type="text" id="pregunta" placeholder="Escribe tu mensaje...">
        <br>
        <button onclick="enviarTexto()">📩 Enviar Texto</button>
        <button onclick="grabarVoz()" style="background:#28a745;">🎙️ Hablar</button>
        <p id="status"></p>

        <script>
            async function enviarAIA(texto) {
                document.getElementById('status').innerText = '⏳ Procesando en Gemini...';
                try {
                    let res = await fetch('/asistente', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({pregunta: texto})
                    });
                    if (res.ok) {
                        let blob = await res.blob();
                        let audioUrl = URL.createObjectURL(blob);
                        let audio = new Audio(audioUrl);
                        audio.play();
                        document.getElementById('status').innerText = '🔊 Reproduciendo respuesta...';
                    } else {
                        document.getElementById('status').innerText = '❌ Error en el servidor';
                    }
                } catch(e) {
                    document.getElementById('status').innerText = '❌ Error de conexion: ' + e;
                }
            }

            function enviarTexto() {
                let txt = document.getElementById('pregunta').value;
                if(txt) enviarAIA(txt);
            }

            function grabarVoz() {
                let recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.lang = 'es-ES';
                recognition.start();
                document.getElementById('status').innerText = '🎙️ Escuchando...';
                
                recognition.onresult = function(event) {
                    let text = event.results[0][0].transcript;
                    document.getElementById('pregunta').value = text;
                    enviarAIA(text);
                };
            }
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/asistente', methods=['POST'])
def asistente():
    try:
        pregunta_texto = ""
        if request.is_json:
            data = request.get_json()
            pregunta_texto = data.get("pregunta", "")
        else:
            audio_bytes = request.data
            if not audio_bytes:
                return {"error": "Sin datos"}, 400
            recognizer = sr.Recognizer()
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
                pregunta_texto = recognizer.recognize_google(audio_data, language="es-ES")

        if not pregunta_texto:
            return {"error": "Pregunta invalida"}, 400

        model = obtener_modelo_activo()
        response = model.generate_content(pregunta_texto)
        texto_respuesta = response.text

        tts = gTTS(text=texto_respuesta, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        return send_file(fp, mimetype="audio/mpeg")

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
