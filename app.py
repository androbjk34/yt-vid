from flask import Flask, request, Response
import yt_dlp
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube IPTV VOD Proxy (Railway) OK"

@app.route("/youtube.m3u8")
def youtube_vod():
    video_id = request.args.get("id")
    if not video_id:
        return "Video ID gerekli ?id=VIDEO_ID", 400

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # 🔥 Railway + SSL FIX
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "forcejson": True,

        # SSL / Railway sorun çözümleri
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "prefer_ipv4": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception as e:
        return f"yt-dlp hata: {str(e)}", 500

    if not info or "formats" not in info:
        return "Video bilgisi alınamadı", 500

    # m3u8 (HLS) formatlarını filtrele
    hls_formats = [
        f for f in info["formats"]
        if f.get("protocol") == "m3u8_native" and f.get("url")
    ]

    if not hls_formats:
        return "HLS (m3u8) format bulunamadı", 404

    # En yüksek kaliteyi seç
    best = sorted(
        hls_formats,
        key=lambda x: (x.get("height") or 0),
        reverse=True
    )[0]

    title = info.get("title", "YouTube Video")

    playlist = f"""#EXTM3U
#EXTINF:-1,{title}
{best['url']}
"""

    return Response(
        playlist,
        mimetype="application/vnd.apple.mpegurl"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
