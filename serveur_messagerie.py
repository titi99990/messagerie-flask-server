from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)
messages_store = {}

@app.route("/send", methods=["POST"])
def send_message():
    data = request.get_json()
    to = data.get("to")
    message = data.get("message")
    if not to or not message:
        return jsonify({"error": "Données manquantes."}), 400
    msg_id = str(uuid.uuid4())
    messages_store.setdefault(to, []).append({
        "id": msg_id,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })
    return jsonify({"status": "ok", "id": msg_id})

@app.route("/receive/<public_key>", methods=["GET"])
def receive_messages(public_key):
    return jsonify(messages_store.pop(public_key, []))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
