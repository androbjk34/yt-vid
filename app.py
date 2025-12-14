from flask import Flask, request, Response
import yt_dlp

app = Flask(__name__)

@app.route("/youtube.m3u8")
def youtube_vod():
    video_id = request.args.get("id")
    if not video_id:
        return "Video ID gerekli ?id=VIDEO_ID", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "forcejson": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    # m3u8 formatlarını bul
    hls_formats = [
        f for f in info["formats"]
        if f.get("protocol") == "m3u8_native"
    ]

    if not hls_formats:
        return "HLS (m3u8) format bulunamadı", 404

    # En yüksek kaliteyi seç
    best = sorted(
        hls_formats,
        key=lambda x: (x.get("height") or 0),
        reverse=True
    )[0]

    m3u8_url = best["url"]

    playlist = f"""#EXTM3U
#EXTINF:-1,{info.get('title')}
{m3u8_url}
"""

    return Response(playlist, mimetype="application/x-mpegURL")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)
