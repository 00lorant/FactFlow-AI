
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__, static_folder=".")

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "FactFlow AI"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
