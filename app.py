import yt_dlp

video_url = "https://www.youtube.com/watch?v=VIDEO_ID"

ydl_opts = {
    "quiet": True,
    "skip_download": True,
    "forcejson": True,
    "nocheckcertificate": True,
    "prefer_ipv4": True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=False)

# m3u8 (HLS) formatlarını al
hls_formats = [
    f for f in info.get("formats", [])
    if f.get("protocol") == "m3u8_native"
]

if not hls_formats:
    print("❌ m3u8 bulunamadı")
else:
    # En yüksek kalite
    best = sorted(
        hls_formats,
        key=lambda x: (x.get("height") or 0),
        reverse=True
    )[0]

    print("✅ Öncelikli (best) m3u8 linki:\n")
    print(best["url"])
