import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from os import path

load_dotenv()

app = Flask(__name__)
CORS(app)


DB_FILE = os.path.join(os.path.dirname(__file__), "calls.db")
DB_URL = f"sqlite:///{DB_FILE}"


app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Call(db.Model):
    __tablename__ = "calls"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    call_id = db.Column(db.String, unique=True)
    firstName = db.Column(db.String)
    lastName = db.Column(db.String)
    email = db.Column(db.String)
    phone = db.Column(db.String)
    productName = db.Column(db.String)
    issue = db.Column(db.Text)
    resolutionStatus = db.Column(db.String)
    call_start = db.Column(db.String)
    call_end = db.Column(db.String)
    summary = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'email': self.email,
            'phone': self.phone,
            'productName': self.productName,
            'issue': self.issue,
            'resolutionStatus': self.resolutionStatus,
            'call_start': self.call_start,
            'call_end': self.call_end,
            'summary': self.summary
        }


with app.app_context():
    db.create_all()

# ---------------------------------------------------------------------

def fetch_call_details(call_id):
    url = f"https://api.vapi.ai/call/{call_id}"
    headers = {
        "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}"
    }
    response = requests.get(url, headers=headers)
    return response.json()

@app.route("/call-details", methods=["GET"])
def get_call_details():
    call_id = request.args.get("call_id")
    if not call_id:
        return jsonify({"error": "Call ID is required"}), 400
    
    try:
        response = fetch_call_details(call_id)
        
        summary = response.get("summary")
        analysis = response.get("analysis")
        
        assistant_overrides = response.get("assistantOverrides", {})
        variable_values = assistant_overrides.get("variableValues", {})
        
        structured_data = analysis.get("structuredData", {}) if analysis else {}
        
        existing_call = Call.query.filter_by(call_id=call_id).first()
        if existing_call:
            existing_call.firstName = variable_values.get("firstName")
            existing_call.lastName = variable_values.get("lastName")
            existing_call.email = variable_values.get("email")
            existing_call.phone = variable_values.get("phone")
            existing_call.call_start = response.get("startedAt")
            existing_call.call_end = response.get("endedAt")
            existing_call.summary = summary
            existing_call.productName = structured_data.get("productName", "")
            existing_call.issue = structured_data.get("issueDescription", "")
            existing_call.resolutionStatus = structured_data.get("resolutionStatus", "")
            call_record = existing_call
        else:
            
            call_record = Call(
                call_id=call_id,  
                firstName=variable_values.get("firstName"),
                lastName=variable_values.get("lastName"),
                email=variable_values.get("email"),
                phone=variable_values.get("phone"),
                call_start=response.get("startedAt"),
                call_end=response.get("endedAt"),
                summary=summary,
                productName=structured_data.get("productName", ""),
                issue=structured_data.get("issueDescription", ""),
                resolutionStatus=structured_data.get("resolutionStatus", "")
            )
            db.session.add(call_record)
        
        
        db.session.commit()
        print("Database updated")
        
        return jsonify({
            "call": call_record.to_dict(),
            "analysis": analysis,
            "summary": summary
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)