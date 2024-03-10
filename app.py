from flask import Flask, render_template, request, url_for, redirect, session
from authlib.integrations.flask_client import OAuth
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag
import psycopg2
import requests
from urllib.error import HTTPError
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

oauth = OAuth(app)

app.config['SECRET_KEY'] = "Pankaj"
app.config['GITHUB_CLIENT_ID'] = "37b853ae7b5c2741647e"
app.config['GITHUB_CLIENT_SECRET'] = "fe7aa41a6d561652f25ca34881d8604f165ee6a9"

github = oauth.register(
    name='github',
    client_id=app.config["GITHUB_CLIENT_ID"],
    client_secret=app.config["GITHUB_CLIENT_SECRET"],
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

DB_NAME = "news24"  # Update with your actual database name
DB_USER = "news24_user"
DB_PASSWORD = "DWPCmdYxVs4yp505uH7hXZ0vmaGWxROc"
DB_HOST = "dpg-cnmkjv2cn0vc738elb40-a"

VIEW_DATA_PASSWORD = "pk12112004"

def connect_to_database():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)

def insert_into_database(text, num_sentences, num_words, num_stop_words, upos_tag):
    connection = connect_to_database()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO text_news(input_text, num_sentences, num_words, num_stop_words, upos_tag) VALUES (%s, %s, %s, %s, %s)",
        (text, num_sentences, num_words, num_stop_words, upos_tag)
    )
    connection.commit()
    connection.close()

def remove_punctuation(lst):
    lst1 = ['!', ',', '.', '?', '-', '"', ':', ';', '/', '_']
    count = 0
    for i in lst:
        if i not in lst1:
            count += 1
    return count

@app.route('/',methods=['GET','POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        try:
            html = requests.get(url).text
            soup = BeautifulSoup(html, "html.parser")
            heading = soup.find('h1', class_="jsx-ace90f4eca22afc7 Story_strytitle__MYXmR")
            subheading = soup.find('h2', class_="jsx-ace90f4eca22afc7")
            title = (heading.text if heading else "") + (subheading.text if subheading else "")

            main_content = soup.find('div', class_="jsx-ace90f4eca22afc7 Story_description__fq_4S description paywall")
            if main_content:
                for i in main_content.find_all('div', class_=['authors__container', 'tab-link', "end_story_embed_label", "story__recommended__chunk", "ads__container inline-story-add inline_ad1"]):
                    i.decompose()
                clean_content = title + main_content.text
                cleantext = re.sub(r'<.*?>', '', str(clean_content))

                # Task 1: Analyze text
                sentences = sent_tokenize(cleantext)
                words = word_tokenize(cleantext)
                stop_words = set(stopwords.words('english'))

                def count_words_without_punctuation(cleantext):
                    words = word_tokenize(cleantext)
                    return remove_punctuation(words)

                # UPOS tags
                pos_tags = pos_tag(words, tagset='universal')
                upos_tag_count = {}  # Initialize as an empty dictionary
                for tag in pos_tags:
                    upos_tag_count[tag[1]] = upos_tag_count.get(tag[1], 0) + 1

                # Task 2: Save to PostgreSQL
                insert_into_database(cleantext, len(sentences), count_words_without_punctuation(cleantext),
                                      len([word for word in words if word.lower() in stop_words]), str(upos_tag_count))

                return render_template('index.html', cleantext=cleantext)
            else:
                return "Main content not found in the provided URL."

        except requests.exceptions.RequestException:
            return "Invalid URL or Unable to access the URL."

    return render_template('index.html')

@app.route('/view_data', methods=['GET', 'POST'])
def view_data():
    if request.method == 'POST' and request.form.get('password') == VIEW_DATA_PASSWORD:
        connection = connect_to_database()
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM text_news")
        data = cursor.fetchall()

        connection.close()

        return render_template('history.html', data=data)

    return render_template('password_prompt.html')


# Github login route
@app.route('/login/github')
def github_login():
    github = oauth.create_client('github')
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

# Github authorize route
@app.route('/login/github/authorize')
def github_authorize():
    github = oauth.create_client('github')
    token = github.authorize_access_token()
    session['github_token'] = token
    resp = github.get('user').json()
    print(f"\n{resp}\n")
    connection = connect_to_database()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM text_news")
    data = cursor.fetchall()

    connection.close()

    return render_template('history.html', data=data)
    # Redirect to a template or another route after successful authorization

# Logout route for GitHub
@app.route('/logout/github')
def github_logout():
    session.pop('github_token', None)
    return redirect(url_for('index1'))

if __name__ == '__main__':
    app.run(debug=True)
