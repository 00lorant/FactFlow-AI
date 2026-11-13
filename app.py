
from flask import Flask, send_from_directory, jsonify, request
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, concatenate_videoclips
import os
import uuid
import threading
import re
import textwrap

app = Flask(__name__, static_folder=".")

jobs = {}

VIDEO_DIR = "static/videos"
SCENE_DIR = "static/scenes"

os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(SCENE_DIR, exist_ok=True)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "app": "FactFlow AI"
    })


def get_font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def create_scene(text, scene_number, total_scenes, width, height, path):
    image = Image.new("RGB", (width, height), "#090d18")
    draw = ImageDraw.Draw(image)

    title_font = get_font(25)
    body_font = get_font(29)
    small_font = get_font(18)

    draw.rounded_rectangle(
        (25, 25, width - 25, height - 25),
        radius=25,
        outline="#7565f6",
        width=3
    )

    draw.text(
        (width // 2, 75),
        "FACTFLOW AI",
        fill="#a99fff",
        font=title_font,
        anchor="mm"
    )

    draw.line(
        (width // 2 - 55, 115, width // 2 + 55, 115),
        fill="#409eea",
        width=3
    )

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = current + " " + word if current else word
        if draw.textbbox((0, 0), test, font=body_font)[2] > width - 100:
            if current:
                lines.append(current)
            current = word
        else:
            current = test

    if current:
        lines.append(current)

    line_height = 48
    total_height = len(lines) * line_height
    y = (height - total_height) // 2

    for line in lines:
        draw.text(
            (width // 2, y),
            line,
            fill="#f4f7fb",
            font=body_font,
            anchor="mm"
        )
        y += line_height

    draw.text(
        (width // 2, height - 75),
        f"SCENE {scene_number} / {total_scenes}",
        fill="#9aa8bd",
        font=small_font,
        anchor="mm"
    )

    image.save(path)


def render_video(job_id):
    job = jobs[job_id]

    try:
        job["status"] = "rendering"
        job["message"] = "Creating your video scenes..."

        script = job["script"]
        duration_text = job["duration"]

        match = re.search(r"\d+", duration_text)
        minutes = int(match.group()) if match else 1
        total_duration = max(60, min(minutes * 60, 600))

        video_format = job["format"]

        if "Landscape" in video_format:
            width, height = 854, 480
        elif "Square" in video_format:
            width, height = 640, 640
        else:
            width, height = 480, 854

        words = script.split()
        chunks = [
            " ".join(words[i:i + 18])
            for i in range(0, len(words), 18)
        ]

        if not chunks:
            raise ValueError("No text was provided.")

        scene_duration = total_duration / len(chunks)
        clips = []
        scene_folder = os.path.join(SCENE_DIR, job_id)
        os.makedirs(scene_folder, exist_ok=True)

        for index, chunk in enumerate(chunks):
            job["message"] = (
                f"Creating scene {index + 1} of {len(chunks)}..."
            )

            image_path = os.path.join(
                scene_folder,
                f"scene_{index + 1}.jpg"
            )

            create_scene(
                chunk,
                index + 1,
                len(chunks),
                width,
                height,
                image_path
            )

            clip = ImageClip(image_path).with_duration(scene_duration)
            clips.append(clip)

        job["message"] = "Assembling your MP4..."

        final_video = concatenate_videoclips(
            clips,
            method="compose"
        )

        output_path = os.path.join(
            VIDEO_DIR,
            f"{job_id}.mp4"
        )

        final_video.write_videofile(
            output_path,
            fps=15,
            codec="libx264",
            audio=False,
            preset="ultrafast",
            logger=None
        )

        final_video.close()

        for clip in clips:
            clip.close()

        job["status"] = "completed"
        job["message"] = "Your MP4 video is ready."
        job["video_url"] = f"/videos/{job_id}.mp4"

    except Exception as error:
        job["status"] = "failed"
        job["message"] = str(error)


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}

    script = data.get("script", "").strip()

    if not script:
        return jsonify({
            "error": "Please enter a topic or script."
        }), 400

    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "message": "Your video is waiting to be created.",
        "script": script,
        "duration": data.get("duration", "1 minute"),
        "voice": data.get("voice", "Warm and clear"),
        "format": data.get("format", "Vertical 9:16")
    }

    thread = threading.Thread(
        target=render_video,
        args=(job_id,),
        daemon=True
    )
    thread.start()

    return jsonify({
        "job_id": job_id,
        "status": "queued",
        "message": "Your video is being created."
    }), 202


@app.route("/api/status/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)

    if not job:
        return jsonify({
            "error": "Job not found."
        }), 404

    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "message": job["message"],
        "video_url": job.get("video_url")
    })


@app.route("/videos/<filename>")
def download_video(filename):
    return send_from_directory(
        VIDEO_DIR,
        filename,
        as_attachment=True
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
