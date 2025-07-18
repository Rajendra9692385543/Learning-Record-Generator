from flask import Flask, render_template, request, session, redirect, url_for, make_response
import requests
import wikipedia
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime

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
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
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

if __name__ == '__main__':
    app.run(debug=True)
