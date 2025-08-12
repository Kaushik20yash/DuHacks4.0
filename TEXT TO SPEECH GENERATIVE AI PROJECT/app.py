from flask import Flask, request, jsonify, send_file, render_template, url_for
from googletrans import Translator
from gtts import gTTS
from langdetect import detect
import os
import uuid

import fitz
import docx

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LANGUAGE_CODES = {
    'English': 'en', 'French': 'fr', 'Hindi': 'hi', 'Spanish': 'es', 'German': 'de',
    'Italian': 'it', 'Chinese': 'zh-cn', 'Japanese': 'ja', 'Arabic': 'ar',
    'Russian': 'ru', 'Bengali': 'bn', 'Turkish': 'tr', 'Urdu': 'ur'
}

ACCENT_TLDS = {
    'US': 'com', 'UK': 'co.uk', 'India': 'co.in', 'Canada': 'ca', 'Australia': 'com.au'
}


@app.route('/')
def home():
    return render_template('main.html')


@app.route('/text_to_speech')
def text_to_speech():
    return render_template(
        'text_to_speech.html',
        languages=LANGUAGE_CODES.keys(),
        accents=ACCENT_TLDS.keys()
    )


@app.route('/docx_pdf_speech')
def docx_pdf_speech():
    return render_template(
        'docx_pdf_speech.html',
        languages=LANGUAGE_CODES.keys(),
        accents=ACCENT_TLDS.keys()
    )


@app.route('/download/<filename>')
def download_audio(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(path, mimetype='audio/mpeg')


@app.route('/process-tts', methods=['POST'])
def process_tts():
    text = request.form.get('text')
    language_name = request.form.get('target_language')
    accent_name = request.form.get('accent')

    target_language = LANGUAGE_CODES.get(language_name)
    accent = ACCENT_TLDS.get(accent_name, 'com')

    if not text or not target_language:
        return jsonify({'error': 'Missing input'}), 400

    detected_lang = detect(text)
    translated = Translator().translate(text, src=detected_lang, dest=target_language).text

    try:
        tts = gTTS(text=translated, lang=target_language, tld=accent)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    filename = f"{uuid.uuid4().hex}.mp3"
    path = os.path.join(UPLOAD_FOLDER, filename)
    tts.save(path)

    return jsonify({
        'translated_text': translated,
        'audio_url': url_for('download_audio', filename=filename)
    })


# @app.route('/process-translation', methods=['POST'])
# def process_translation():
#     text = request.form.get('text')
#     language_name = request.form.get('target_language')

#     target_language = LANGUAGE_CODES.get(language_name)
#     if not text or not target_language:
#         return jsonify({'error': 'Missing input'}), 400

#     detected_lang = detect(text)
#     translated = Translator().translate(text, src=detected_lang, dest=target_language).text
#     return jsonify({'translated_text': translated})


@app.route('/process-doc', methods=['POST'])
def process_doc():
    file = request.files.get('file')
    language_name = request.form.get('target_language')
    accent_name = request.form.get('accent')

    if not file or not language_name:
        return jsonify({'error': 'Missing file or language'}), 400

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    ext = os.path.splitext(filename)[1].lower()
    extracted_text = ""

    try:
        if ext == '.docx':
            doc = docx.Document(file_path)
            extracted_text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == '.pdf':
            pdf_doc = fitz.open(file_path)
            extracted_text = "\n".join([page.get_text() for page in pdf_doc])
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to extract text: {e}'}), 500

    if not extracted_text.strip():
        return jsonify({'error': 'No readable text found in the document'}), 400

    target_language = LANGUAGE_CODES.get(language_name)
    accent = ACCENT_TLDS.get(accent_name, 'com')

    try:
        detected_lang = detect(extracted_text)
        translator = Translator()
        translated = translator.translate(extracted_text, src=detected_lang, dest=target_language).text
        tts = gTTS(text=translated, lang=target_language, tld=accent)
    except Exception as e:
        return jsonify({'error': f'Translation or TTS error: {e}'}), 500

    audio_filename = f"{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(UPLOAD_FOLDER, audio_filename)
    tts.save(audio_path)

    return jsonify({
        'translated_text': translated,
        'audio_url': url_for('download_audio', filename=audio_filename)
    })

@app.route('/download/<filename>')
def download_doc_audio(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    return send_file(path, mimetype='audio/mpeg')


if __name__ == '__main__':
    app.run(debug=True)
