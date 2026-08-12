import os
import io
import re
import gc
from flask import Flask, request, send_file, render_template_string
import google.generativeai as genai
from gtts import gTTS

app = Flask(__name__)

# Configuración de la API Key desde las variables de Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "TU_API_KEY_AQUI")
genai.configure(api_key=GEMINI_API_KEY)

INSTRUCCION_SISTEMA = (
    "Responde siempre de forma muy breve, concisa y directa (máximo 2 oraciones). "
    "No utilices formatos especiales, listas ni asteriscos."
)

def consultar_gemini(prompt):
    # 1. Probar lista de modelos estáticos comunes
    modelos_estaticos = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    for m_nombre in modelos_estaticos:
        try:
            try:
                model = genai.GenerativeModel(m_nombre, system_instruction=INSTRUCCION_SISTEMA)
            except Exception:
                model = genai.GenerativeModel(m_nombre)
                
            response = model.generate_content(prompt)
            if response and response.text:
                print(f"[SERVIDOR] Respuesta exitosa con modelo estático: {m_nombre}")
                return response.text
        except Exception as e:
            print(f"[SERVIDOR] Modelo {m_nombre} no disponible: {e}")
            continue

    # 2. Si fallan los nombres fijos, detectar modelos habilitados dinámicamente
    print("[SERVIDOR] Consultando modelos disponibles en tu API Key...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                try:
                    m_dinamico = genai.GenerativeModel(m.name)
                    response = m_dinamico.generate_content(f"{INSTRUCCION_SISTEMA}\n\nPregunta: {prompt}")
                    if response and response.text:
                        print(f"[SERVIDOR] Respuesta exitosa con modelo dinámico: {m.name}")
                        return response.text
                except Exception as inner_e:
                    print(f"[SERVIDOR] Falló modelo dinámico {m.name}: {inner_e}")
                    continue
    except Exception as list_e:
        print(f"[SERVIDOR] Error al listar modelos: {list_e}")

    raise Exception("No se pudo conectar con ningún modelo Gemini. Revisa la GEMINI_API_KEY en Render.")

def limpiar_texto(texto):
    # Remover asteriscos, carácteres de formato e hipermarcado
    texto_limpio = re.sub(r'[*#_`~]', '', texto)
    return texto_limpio.strip()

# ------------------------------------------------------------------
# INTERFAZ WEB PARA EL CELULAR
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
            input { width: 85%; padding: 12px; font-size: 16px; border-radius: 8px; border: none; margin: 10px 0; box-sizing: border-box; }
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
                        let errJson = await res.json().catch(() => ({}));
                        document.getElementById('status').innerText = '❌ Error: ' + (errJson.error || 'Servidor HTTP ' + res.status);
                    }
                } catch(e) {
                    document.getElementById('status').innerText = '❌ Error de conexión: ' + e;
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
            pregunta_texto = request.data.decode('utf-8', errors='ignore')

        if not pregunta_texto:
            return {"error": "Pregunta vacia"}, 400

        print(f"[SERVIDOR] Pregunta recibida: {pregunta_texto}")
        
        # Consultar Gemini
        respuesta_raw = consultar_gemini(pregunta_texto)
        respuesta_limpia = limpiar_texto(respuesta_raw)
        print(f"[SERVIDOR] Respuesta limpia: {respuesta_limpia}")

        # Generar audio MP3
        tts = gTTS(text=respuesta_limpia, lang='es')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)

        # Liberar memoria RAM en Render
        gc.collect()

        return send_file(fp, mimetype="audio/mpeg")

    except Exception as e:
        print(f"[ERROR SERVIDOR]: {e}")
        gc.collect()
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
