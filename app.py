from flask import Flask, render_template, request, session, redirect, url_for, make_response
import requests
import wikipedia
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime
''' import os
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import fitz  # PyMuPDF '''


app = Flask(__name__)
app.secret_key = "your_secret_key"  # ✅ Required for using sessions

TOGETHER_API_KEY = "tgp_v1_DO5SSD_OB4QavZWae4xRvJHF-xTRWL2c5xaXXUYqheE"

def get_topic_context(topic):
    try:
        # Use auto-suggestion to catch similar matches
        return wikipedia.summary(topic, sentences=4, auto_suggest=True)
    except wikipedia.exceptions.DisambiguationError as e:
        return f"(Note: Topic ambiguous. Suggestions: {', '.join(e.options[:3])})"
    except wikipedia.exceptions.PageError:
        return "(Note: Topic not found on Wikipedia.)"
    except Exception as e:
        return f"(Error fetching context: {str(e)})"


def generate_learning_record(topic):
    context = get_topic_context(topic)

    prompt = f"""
You are an education expert creating structured academic learning records for college students.

Topic: {topic}

Summary for reference:
{context}

Using the topic and context above, generate a structured Learning Record in this exact format:

======================

Name of the Topic:  
{topic}  

Learning Outcome:  
 (3 bullet points)

Concepts Learned (Mention 2/3 Principles):  
 Definition: (1-line)  
 Characteristics: (2–3 points)  
 Design Principles/Techniques: (2–3 points)

New Techniques Learned (as applicable):  
 (3 techniques)

New Software/Machine/Tool/Equipment/Experiment Learned:  
 (List 3 OR say 'Not Applicable')

Application of Concept(s) (Preferably Real-Life Scenario):  
 (3 applications)

Case Studies/Examples:  
 Example 1: (1-line real-world example)  
 Example 2: (1-line real-world example)

======================

Only generate what's inside the lines above. Be concise, clear, and structured.
"""

    payload = {
        "model": "meta-llama-3.3-70b-instruct-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert teacher writing structured learning records for students."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.7,
        "top_p": 0.95
    }

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        result = response.json()
        print("📩 API Raw Result:", result)

        if 'choices' in result and result['choices']:
            message = result['choices'][0]['message']['content'].strip()
            if message:
                return message
            else:
                print("⚠️ Empty message returned.")
                return "⚠️ Failed to generate learning record. Try again."
        else:
            print("⚠️ No choices returned.")
            return "⚠️ Failed to generate learning record. Try again."

    except Exception as e:
        print("❌ API error:", e)
        return f"❌ API request failed: {str(e)}"


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'records' not in session:
        session['records'] = []

    if request.method == 'POST':
        topic = request.form['topic'].strip()
        print(f"🔍 User submitted topic: {topic}")

        record = generate_learning_record(topic)
        print(f"✅ Generated record (length {len(record)}):", record[:150])  # First 150 chars

        session['records'].append(record)
        session['flash'] = f'Topic \"{topic}\" added successfully!'
        session.modified = True

        print(f"🧾 Total records in session now: {len(session['records'])}")
        return redirect(url_for('index'))

    flash_message = session.pop('flash', None)
    return render_template('index.html', records=session['records'], flash=flash_message)

@app.route('/reset')
def reset():
    session.pop('records', None)
    return redirect(url_for('index'))


@app.route('/preview')
def preview():
    records = session.get('records', [])
    return render_template('preview.html', records=records)


@app.route('/generate_pdf')
def generate_pdf():
    records = session.get('records', [])
    html = render_template('pdf_template.html', records=records)
    result = BytesIO()
    pisa.CreatePDF(html, dest=result)
    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=Learning_Records.pdf'
    return response

#Assignment Logic 

@app.route('/assignment', methods=['GET', 'POST'])
def assignment():
    if 'assignments' not in session:
        session['assignments'] = []

    if request.method == 'POST':
        questions_raw = request.form['questions'].strip()
        word_limit = request.form['word_limit'].strip()

        questions = [q.strip() for q in questions_raw.split('\n') if q.strip()]
        responses = []

        for q in questions:
            prompt = f"Answer the following question in about {word_limit} words:\n\nQuestion: {q}"
            payload = {
                "model": "meta-llama-3.3-70b-instruct-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a subject expert writing concise answers for student assignments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.7,
                "top_p": 0.9
            }

            headers = {
                "Authorization": f"Bearer {TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(
                    "https://api.together.xyz/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                result = response.json()
                if 'choices' in result and result['choices']:
                    answer = result['choices'][0]['message']['content'].strip()
                    responses.append((q, answer))
                else:
                    responses.append((q, "⚠️ Could not generate answer."))
            except Exception as e:
                responses.append((q, f"❌ Error: {str(e)}"))

        session['assignments'] = responses
        session['flash'] = f"✅ {len(responses)} answers generated successfully!"
        session.modified = True
        return redirect(url_for('assignment'))

    flash = session.pop('flash', None)
    return render_template('assignment.html', answers=session.get('assignments', []), flash=flash)

@app.route('/reset_assignment')
def reset_assignment():
    session.pop('assignments', None)
    return redirect(url_for('assignment'))

@app.route('/preview_assignment')
def preview_assignment():
    return render_template('assignment_preview.html', answers=session.get('assignments', []))

@app.route('/generate_assignment_pdf')
def generate_assignment_pdf():
    html = render_template('assignment_pdf.html', answers=session.get('assignments', []))
    result = BytesIO()
    pisa.CreatePDF(html, dest=result)
    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=Assignment_Answers.pdf'
    return response

''' #Question Answering Logic

# Required earlier in your app.py
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ Generate answers from extracted questions ------------------

def generate_answers_from_questions(questions, word_limit=50):
    all_qna = []
    for q in questions:
        prompt = f"Answer the following question in about {word_limit} words:\nQ: {q}"
        payload = {
            "model": "meta-llama-3.3-70b-instruct-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert helping students answer academic questions."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.95
        }
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            res = requests.post("https://api.together.xyz/v1/chat/completions", json=payload, headers=headers, timeout=30)
            data = res.json()
            answer = data['choices'][0]['message']['content'].strip()
        except:
            answer = "⚠️ Failed to generate answer."
        all_qna.append((q, answer))
    return all_qna


# ------------------ Extract questions from image ------------------

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    questions = [line.strip() for line in text.split("\n") if line.strip()]
    return questions

# ------------------ Extract from PDF ------------------

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    questions = [line.strip() for line in text.split("\n") if line.strip()]
    return questions


# ------------------ Routes ------------------

@app.route('/solve_paper', methods=['GET', 'POST'])
def solve_paper():
    if 'solved_qna' not in session:
        session['solved_qna'] = []

    if request.method == 'POST':
        file = request.files['file']
        word_limit = int(request.form.get('word_limit', 50))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            ext = filename.rsplit('.', 1)[1].lower()
            if ext == 'pdf':
                questions = extract_text_from_pdf(filepath)
            else:
                questions = extract_text_from_image(filepath)

            if questions:
                answers = generate_answers_from_questions(questions, word_limit)
                session['solved_qna'] = answers
                session.modified = True
                session['flash'] = f"{len(answers)} questions processed successfully."
            else:
                session['flash'] = "No text found in the uploaded file."

        return redirect(url_for('solve_paper'))

    flash_msg = session.pop('flash', None)
    return render_template('question_paper.html', answers=session.get('solved_qna', []), flash=flash_msg)


@app.route('/reset_solve')
def reset_solve():
    session.pop('solved_qna', None)
    return redirect(url_for('solve_paper'))


@app.route('/preview_solve')
def preview_solve():
    qna = session.get('solved_qna', [])
    return render_template('question_paper_preview.html', answers=qna)


@app.route('/generate_solve_pdf')
def generate_solve_pdf():
    qna = session.get('solved_qna', [])
    html = render_template('question_paper_pdf.html', answers=qna)
    result = BytesIO()
    pisa.CreatePDF(html, dest=result)
    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=Question_Paper_Solution.pdf'
    return response '''

@app.route('/coming-soon')
def coming_soon():
    return render_template('under_construction.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0")
