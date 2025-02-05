from app.models import db, Response

def flag_response(response_id, flagged_for_review, review_notes):
    response = Response.query.get(response_id)
    if response:
        response.flagged_for_review = flagged_for_review
        response.review_notes = review_notes
        db.session.commit()
        return True
    return False