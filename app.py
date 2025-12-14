from flask import Flask, request, Response
import yt_dlp
import os
import requests
from urllib.parse import urljoin, quote

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

@app.route("/")
def home():
    return "YouTube IPTV FULL PROXY OK"

@app.route("/youtube.m3u8")
def youtube_vod():
    video_id = request.args.get("id")
    if not video_id:
        return "id gerekli", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "forcejson": True,
        "nocheckcertificate": True,
        "prefer_ipv4": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    hls = [f for f in info["formats"] if f.get("protocol") == "m3u8_native"]
    if not hls:
        return "m3u8 yok", 404

    source_m3u8 = hls[-1]["url"]

    r = requests.get(source_m3u8, headers=HEADERS, timeout=10)
    base = source_m3u8.rsplit("/", 1)[0] + "/"

    out = "#EXTM3U\n"

    for line in r.text.splitlines():
        if line.startswith("#"):
            out += line + "\n"
        else:
            absolute = urljoin(base, line)
            out += f"/proxy?url={quote(absolute)}\n"

    return Response(out, mimetype="application/vnd.apple.mpegurl")


@app.route("/proxy")
def proxy():
    url = request.args.get("url")
    if not url:
        return "url yok", 400

    r = requests.get(url, headers=HEADERS, stream=True, timeout=10)
    return Response(
        r.iter_content(chunk_size=8192),
        status=r.status_code,
        headers={"Content-Type": r.headers.get("Content-Type", "application/octet-stream")}
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
