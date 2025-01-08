from flask import Flask, render_template, request, redirect, url_for
import data_access
import story_builder
import database

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_story', methods=['GET', 'POST'])
def add_story():
    if request.method == 'POST':
        story_content = request.form['story_content']
        connection = database.connect()
        database.add_story(connection, story_content)
        connection.close()
        return redirect(url_for('index'))
    return render_template('add_story.html')

@app.route('/see_all_stories')
def see_all_stories():
    connection = database.connect()
    stories = data_access.see_all_stories_for_HTML(connection)
    connection.close()
    print(stories)
    return render_template('see_all_stories.html', stories=stories)

@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if request.method == 'POST':
        question_content = request.form['question_content']
        connection = database.connect()
        data_access.add_question(connection, question_content)
        connection.close()
        return redirect(url_for('index'))
    return render_template('add_question.html')

@app.route('/see_all_questions')
def see_all_questions():
    connection = database.connect()
    questions = data_access.get_all_questions(connection)
    connection.close()
    return render_template('see_all_questions.html', questions=questions)

if __name__ == '__main__':
    app.run(debug=True)