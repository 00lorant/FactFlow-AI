from flask import Flask, send_from_directory, jsonify, request
import os
import uuid
import threading

app = Flask(__name__, static_folder=".")

jobs = {}

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "FactFlow AI"
    })

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    script = data.get("script", "").strip()
    duration = data.get("duration", "1 minute")
    voice = data.get("voice", "Warm and clear")
    video_format = data.get("format", "Vertical 9:16")

    if not script:
        return jsonify({"error": "Please enter a script."}), 400

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "message": "Your video request has been received.",
        "script": script,
        "duration": duration,
        "voice": voice,
        "format": video_format
    }

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "message": "Your video request was received."
    }), 202

@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found."}), 404

    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "message": job["message"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
