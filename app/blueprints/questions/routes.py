from flask import flash, render_template, request, redirect, url_for, session, jsonify
from ...services import  question_service
from . import questions_bp



@questions_bp.route('/list')
def list():
    questions = question_service.get_all_questions()
    return render_template('see_all_questions_updated.html', questions=questions)

@questions_bp.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        question_content = request.form.get('question_content')
        if question_content:
            try:
                question_id = question_service.add_question(question_content)
                session['question_id'] = question_id
                #session['question_content'] = question_content
                #flash(f"Question added successfully!", "success")
            except Exception as e:
                flash(f"Error adding question: {e}", "danger")
        return redirect(url_for('questions.list'))
    return render_template('see_all_questions_updated.html') #removed add_question after testing as no longer use it. 
#Must not be hitting this part of the route as didn't see until now.

@questions_bp.route('/select', methods=['GET', 'POST'])
def select():
    if request.method == 'POST':
        question_id = request.form.get('question_id')
        if question_id:
            session['question_id'] = question_id
            # Next step would be selecting a model
            return redirect(url_for('llm.select_model'))
    else:
        questions = question_service.get_all_questions()
        return render_template('see_all_questions_updated.html', questions=questions)

@questions_bp.route('/update_selection', methods=['POST'])
def update_selection():
    data = request.get_json()
    
    # Check if we're clearing the selection
    if data.get('clear'):
        if 'question_id' in session:
            session.pop('question_id')
        # if 'question_content' in session: #shouldn't be needed any more since question_content no longer being added to session (I think)
        #     session.pop('question_content')
        return jsonify({'success': True})
    
    # Otherwise update the question selection
    question_id = data.get('question_id')
    if question_id:
        # Verify the question exists
        question = question_service.get_question_by_id(question_id)
        if question:
            # Used to store both ID and content in session - convenient but can lead to inconsistencies
            session['question_id'] = question_id
            #session['question_content'] = question.content            
            
            return jsonify({
                'success': True,
                'question_id': question_id,
                # 'content': question.content
            })
        return jsonify({'success': False, 'message': 'Question not found'}), 404
    
    return jsonify({'success': False, 'message': 'No question_id provided'}), 400