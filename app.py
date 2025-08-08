# Flask framework import kar rahe hain web application banane ke liye
from flask import Flask, request, jsonify, render_template, send_file
import os, shutil, json, base64
from werkzeug.utils import secure_filename
from PIL import Image
from openai import OpenAI
from datetime import datetime

# PDF (ReportLab) + Urdu shaping/bidi
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer,Flowable
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)
client = OpenAI()

CHAPTERS_DIR = 'chapters'
FONTS_DIR = 'fonts'
URDU_FONT_FILE = os.path.join(FONTS_DIR, 'NotoNaskhArabic-Regular.ttf')
URDU_FONT_NAME = 'NotoNaskhArabic'

if not os.path.exists(CHAPTERS_DIR):
    os.makedirs(CHAPTERS_DIR)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

def process_folder_images_batch(chapter_path):
    try:
        image_files = [f for f in os.listdir(chapter_path)
                       if os.path.isfile(os.path.join(chapter_path, f))
                       and allowed_file(f)]
        if not image_files:
            return None

        content_array = [{"type": "text", "text": "Process all images. JSON only."}]
        for image_file in image_files:
            image_path = os.path.join(chapter_path, image_file)
            base64_image = encode_image_to_base64(image_path)
            if base64_image:
                content_array.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                })

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=900,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are an exam notes generator. Detect ALL questions in EACH image and return JSON only: [{question, answer_en, answer_ur}]. Keep answers concise and exam-accurate; add symbols/formulas/examples only when needed for marks. No explanations, no markdown—JSON array only."
                },
                {"role": "user", "content": content_array}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error processing folder images: {e}")
        return None

# ------------ Urdu PDF utilities (FIXED BASELINE) ------------

def register_urdu_font_once():
    try:
        if URDU_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            if os.path.exists(URDU_FONT_FILE):
                pdfmetrics.registerFont(TTFont(URDU_FONT_NAME, URDU_FONT_FILE))
                print(f"✅ Registered Urdu font: {URDU_FONT_NAME}")
            else:
                print(f"⚠️ Urdu font not found at {URDU_FONT_FILE}")
    except Exception as e:
        print(f"⚠️ Urdu font register failed: {e}")

def urdu_shape(text: str) -> str:
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(text))


def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ------- NEW: RTL Flowable with manual wrapping -------
def split_rtl_lines(text, font_name, font_size, max_width):
    # text must be already shaped with urdu_shape()
    words = text.split(' ')
    lines, current = [], ""
    for w in words:
        test = (w if not current else current + " " + w)
        width = pdfmetrics.stringWidth(test, font_name, font_size)
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines

class RTLParagraph(Flowable):
    def __init__(self, text, font_name, font_size=14, color=HexColor("#1976D2"), leading=None, padding_y=2):
        super().__init__()
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.leading = leading or int(font_size * 1.55)  # ample line height => baseline ok
        self.padding_y = padding_y
        self._lines = []
        self._width = 0

    def wrap(self, availWidth, availHeight):
        self._width = availWidth
        self._lines = split_rtl_lines(self.text, self.font_name, self.font_size, availWidth)
        height = len(self._lines) * self.leading + self.padding_y*2
        return availWidth, height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFont(self.font_name, self.font_size)
        c.setFillColor(self.color)
        # Flowable origin is at lower-left of its box
        y = self.leading * (len(self._lines)-1)  # top line position
        for i, line in enumerate(self._lines):
            # right align each line to the flowable width
            c.drawRightString(self._width, y - i*self.leading, line)
        c.restoreState()

# ------- Watermark canvas (aapka hi) -------
class WatermarkCanvas(canvas.Canvas):
    def showPage(self):
        self._draw_watermark()
        super().showPage()
    def save(self):
        self._draw_watermark()
        super().save()
    def _draw_watermark(self):
        try:
            self.saveState()
            self.setFont("Helvetica-Bold", 50)
            try:
                self.setFillColor(Color(0.9, 0.9, 0.9, alpha=0.2))
            except Exception:
                self.setFillColor(HexColor('#E5E7EB'))
            self.rotate(45)
            self.drawString(200, 100, "GoodWill")
            self.setFont("Helvetica", 20)
            self.drawString(220, 50, "Educational Content")
        finally:
            self.restoreState()

# ------- REPLACE this function with the one below -------
def create_beautiful_pdf(chapter_name, questions_data):
    try:
        register_urdu_font_once()
        font_available = (URDU_FONT_NAME in pdfmetrics.getRegisteredFontNames())

        # Parse tolerantly
        if isinstance(questions_data, str):
            try:
                data = json.loads(questions_data)
            except Exception:
                js = questions_data[questions_data.find('{'):questions_data.rfind('}')+1]
                data = json.loads(js) if js.strip().startswith('{') else {"questions": []}
        else:
            data = questions_data or {"questions": []}
        questions = data.get("questions", [])

        pdf_path = os.path.join(CHAPTERS_DIR, secure_filename(chapter_name), f"{chapter_name}_notes.pdf")
        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            rightMargin=60, leftMargin=60, topMargin=80, bottomMargin=60,
            canvasmaker=WatermarkCanvas
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleX', parent=styles['Heading1'],
                                     fontSize=26, leading=32, alignment=TA_CENTER,
                                     spaceAfter=18, textColor=HexColor("#2C3E50"),
                                     fontName='Helvetica-Bold')
        question_style = ParagraphStyle('Q', parent=styles['Normal'],
                                        fontSize=14, leading=20, spaceAfter=6,
                                        textColor=HexColor("#34495E"),
                                        fontName='Helvetica-Bold')
        answer_en_style = ParagraphStyle('AEN', parent=styles['Normal'],
                                         fontSize=12, leading=18, spaceAfter=4,
                                         textColor=HexColor("#2E7D32"),
                                         fontName='Helvetica')

        story = []
        # Header
        header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=10,
                                      alignment=TA_RIGHT, textColor=HexColor('#7F8C8D'))
        story.append(Paragraph(f"<b>GoodWill Educational Content</b> | Chapter: {esc(chapter_name)}", header_style))
        story.append(Spacer(1, 16))

        # Title
        story.append(Paragraph(esc(f"{chapter_name}"), title_style))
        story.append(Paragraph(esc("Questions & Answers"), title_style))
        story.append(Spacer(1, 24))

        if not questions:
            story.append(Paragraph("No questions found in the processed data.", styles['Normal']))
        else:
            for i, qa in enumerate(questions, 1):
                # Question
                q = esc(qa.get("question", ""))
                story.append(Paragraph(f"<b>Q{i}. {q}</b>", question_style))
                story.append(Spacer(1, 2))

                # English
                a_en = esc(qa.get("answer_en", ""))
                story.append(Paragraph(f"<b>Answer (English):</b> {a_en}", answer_en_style))

                # Urdu label + answer (RTLParagraph)
                a_ur_raw = qa.get("answer_ur", "").strip()
                if a_ur_raw:
                    label_ur = urdu_shape("جواب (اردو):")
                    # label (separate line)
                    story.append(RTLParagraph(label_ur,
                                              font_name=(URDU_FONT_NAME if font_available else "Helvetica"),
                                              font_size=13,
                                              color=HexColor("#1976D2"),
                                              leading=20))
                    # answer
                    a_ur_shaped = urdu_shape(a_ur_raw)
                    story.append(RTLParagraph(a_ur_shaped,
                                              font_name=(URDU_FONT_NAME if font_available else "Helvetica"),
                                              font_size=14,
                                              color=HexColor("#1976D2"),
                                              leading=22))
                else:
                    story.append(Paragraph(f"<b>Jawab (Urdu):</b> Urdu text not available", answer_en_style))

                story.append(Spacer(1, 8))
                story.append(Paragraph("<hr color='#BDC3C7' width='85%'/>", styles['Normal']))
                story.append(Spacer(1, 10))

        # Footer
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                      fontSize=10, alignment=TA_CENTER, textColor=HexColor('#95A5A6'))
        story.append(Spacer(1, 30))
        story.append(Paragraph("<b>Generated by GoodWill Notes Maker</b><br/>Educational content for exam preparation<br/><i>Study well, succeed better!</i>", footer_style))

        doc.build(story)
        print(f"✅ Beautiful Urdu PDF created (RTL-wrapped): {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error creating PDF: {e}")
        return None
# ------------ End Urdu PDF utilities ------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-chapter', methods=['POST'])
def process_chapter():
    try:
        chapter_data = request.form.get('chaptersData')
        if not chapter_data:
            return jsonify({'error': 'Chapter data not found'}), 400

        chapters_info = json.loads(chapter_data)
        for chapter in chapters_info['chapters']:
            chapter_name = secure_filename(chapter['name'])
            chapter_folder = os.path.join(CHAPTERS_DIR, chapter_name)
            if not os.path.exists(chapter_folder):
                os.makedirs(chapter_folder)

            for image_info in chapter['images']:
                file_key = f"image_{image_info['id']}"
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename != '' and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(chapter_folder, filename))

            print(f"Processing chapter: {chapter_name}")
            print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"User: Waqar-Hassan786")
            
            openai_response = process_folder_images_batch(chapter_folder)
            if openai_response:
                print(f"\n=== OpenAI Response for Chapter: {chapter_name} ===")
                print(openai_response)
                print("=" * 50)
                
                txt_file_path = os.path.join(chapter_folder, f"{chapter_name}_notes.txt")
                with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
                    txt_file.write(f"Chapter: {chapter_name}\n")
                    txt_file.write("=" * 50 + "\n\n")
                    txt_file.write("Questions and Answers (JSON Format):\n")
                    txt_file.write(openai_response)

                try:
                    questions_data = json.loads(openai_response)
                except Exception:
                    questions_data = {"questions": []}
                
                pdf_path = create_beautiful_pdf(chapter_name, questions_data)
                if pdf_path:
                    print(f"✅ PDF created: {pdf_path}")
                else:
                    print(f"❌ PDF creation failed for: {chapter_name}")
                    
        return jsonify({'message': 'Chapter processed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/regenerate-notes', methods=['POST'])
def regenerate_notes():
    try:
        data = request.get_json()
        if not data or 'chapter_name' not in data:
            return jsonify({'error': 'Chapter name not provided'}), 400

        chapter_name = secure_filename(data['chapter_name'])
        chapter_folder = os.path.join(CHAPTERS_DIR, chapter_name)
        if not os.path.exists(chapter_folder):
            return jsonify({'error': 'Chapter folder not found'}), 404

        print(f"Regenerating notes for chapter: {chapter_name}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"User: Waqar-Hassan786")
        
        openai_response = process_folder_images_batch(chapter_folder)
        if openai_response:
            print(f"\n=== Regenerated OpenAI Response for Chapter: {chapter_name} ===")
            print(openai_response)
            print("=" * 50)
            
            txt_file_path = os.path.join(chapter_folder, f"{chapter_name}_notes.txt")
            with open(txt_file_path, 'w', encoding='utf-8') as txt_file:
                txt_file.write(f"Chapter: {chapter_name}\n")
                txt_file.write("=" * 50 + "\n\n")
                txt_file.write("Questions and Answers (JSON Format):\n")
                txt_file.write(openai_response)

            try:
                questions_data = json.loads(openai_response)
            except Exception:
                questions_data = {"questions": []}
            
            pdf_path = create_beautiful_pdf(chapter_name, questions_data)
            if pdf_path:
                print(f"✅ PDF regenerated: {pdf_path}")
            else:
                print(f"❌ PDF regeneration failed for: {chapter_name}")
                
            return jsonify({'message': f'Notes regenerated successfully for {chapter_name}'}), 200
        else:
            return jsonify({'error': 'Failed to regenerate notes'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-notes/<chapter_name>', methods=['GET'])
def download_notes(chapter_name):
    try:
        safe = secure_filename(chapter_name)
        pdf_file_path = os.path.join(CHAPTERS_DIR, safe, f"{safe}_notes.pdf")
        print(f"🔍 Looking for PDF at: {pdf_file_path}")
        if not os.path.exists(pdf_file_path):
            return jsonify({'error': 'PDF file not found'}), 404
        return send_file(
            pdf_file_path,
            as_attachment=True,
            download_name=f"{safe}_notes.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/view-notes/<chapter_name>', methods=['GET'])
def view_notes(chapter_name):
    try:
        safe = secure_filename(chapter_name)
        txt_file_path = os.path.join(CHAPTERS_DIR, safe, f"{safe}_notes.txt")
        if not os.path.exists(txt_file_path):
            return jsonify({'error': 'Notes file not found'}), 404
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'chapter_name': chapter_name, 'content': content, 'file_path': txt_file_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete-chapter', methods=['POST'])
def delete_chapter():
    try:
        data = request.get_json()
        if not data or 'chapter_name' not in data:
            return jsonify({'error': 'Chapter name not provided'}), 400
        safe = secure_filename(data['chapter_name'])
        folder = os.path.join(CHAPTERS_DIR, safe)
        if os.path.exists(folder):
            shutil.rmtree(folder)
            return jsonify({'message': f'Chapter {safe} deleted successfully'}), 200
        else:
            return jsonify({'error': 'Chapter folder not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-chapters', methods=['GET'])
def get_chapters():
    try:
        print(f"Fresh API call for chapters list - User: Waqar-Hassan786")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        chapters = []
        if os.path.exists(CHAPTERS_DIR):
            for folder_name in os.listdir(CHAPTERS_DIR):
                folder_path = os.path.join(CHAPTERS_DIR, folder_name)
                if os.path.isdir(folder_path):
                    image_count = 0
                    has_notes = False
                    has_pdf = False
                    notes_file_date = None
                    for file_name in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file_name)
                        if os.path.isfile(file_path) and allowed_file(file_name):
                            image_count += 1
                        if file_name.endswith('_notes.txt'):
                            has_notes = True
                            notes_file_date = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                        if file_name.endswith('_notes.pdf'):
                            has_pdf = True
                    chapters.append({
                        'name': folder_name,
                        'image_count': image_count,
                        'has_notes': has_notes,
                        'has_pdf': has_pdf,
                        'notes_date': notes_file_date,
                        'created_date': datetime.fromtimestamp(os.path.getctime(folder_path)).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        print(f"Found {len(chapters)} chapters")
        return jsonify({'chapters': chapters}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-fonts')
def debug_fonts():
    exists = os.path.exists(URDU_FONT_FILE)
    registered = URDU_FONT_NAME in pdfmetrics.getRegisteredFontNames()
    return jsonify({
        'cwd': os.getcwd(),
        'font_file': os.path.abspath(URDU_FONT_FILE),
        'font_exists': exists,
        'font_registered': registered,
        'registered_fonts_sample': list(pdfmetrics.getRegisteredFontNames())[:20]
    }), 200

if __name__ == '__main__':
    # Register Urdu font once on startup
    register_urdu_font_once()
    app.run(debug=True, host='0.0.0.0', port=5000)