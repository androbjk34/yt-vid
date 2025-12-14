import os
from flask import Flask, Response, request
import yt_dlp
from urllib.parse import urlparse, parse_qs

# CRITICAL: Gunicorn'un bulması için değişken adı "app" olmalı.
app = Flask(__name__)

# --- Yardımcı Fonksiyonlar ---

def get_youtube_id(url_or_id):
    """
    URL'den veya ID'den geçerli bir YouTube video kimliği (ID) çıkarır.
    """
    processed_input = url_or_id.lstrip('/').replace('https:/', 'https://').replace('http:/', 'http://')
    
    if len(processed_input) == 11 and all(c.isalnum() or c in '-_' for c in processed_input):
        return processed_input
    
    try:
        parsed_url = urlparse(processed_input)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.hostname in ('youtu.be',):
            return parsed_url.path[1:]
    except Exception:
        pass
        
    return None

def get_stream_info(youtube_id):
    """
    yt-dlp kullanarak M3U8/MPD manifestolarını ve akış URL'lerini alır.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    
    ydl_opts = {
        # CRITICAL: m3u8 veya mpd (adaptif akış manifestosu) bulmaya odaklan.
        'format': 'm3u8/mpd/best', 
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True, 
        'retries': 5, 
        # User-Agent, YouTube kısıtlamalarını aşmaya yardımcı olur.
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
    }
    
    stream_url = None
    title = f"YouTube Video ({youtube_id})"

    try:
        # Node.js kurulu olduğu için JS tabanlı formatları artık çözebilir.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            title = info_dict.get('title', title)
            
            if info_dict.get('formats'):
                 for f in info_dict['formats']:
                    url_text = f.get('url', '')
                    if 'm3u8' in url_text:
                        stream_url = url_text
                        break
                    elif 'mpd' in url_text:
                         stream_url = url_text
            
            if not stream_url:
                stream_url = info_dict.get('url') 
                
            if stream_url and stream_url.startswith('http'):
                return stream_url, title
            
            return None, title
            
    except yt_dlp.DownloadError as e:
        print(f"yt-dlp Download Error: {e}") 
        return None, title
    except Exception as e:
        print(f"Genel Hata: {e}")
        return None, title

# --- Flask Rotaları ---

@app.route('/<path:video_id_or_url>')
def generate_dynamic_m3u_playlist(video_id_or_url):
    youtube_id = get_youtube_id(video_id_or_url)

    if not youtube_id:
        return Response(f"#EXTM3U\n#ERROR: Geçersiz YouTube URL veya ID formatı.\n", 
                        mimetype='application/x-mpegurl', status=400)

    stream_url, title = get_stream_info(youtube_id)
    
    if not stream_url:
        return Response(f"#EXTM3U\n#ERROR: '{title}' videosu için yayın linki ALINAMADI. Lütfen Railway loglarını kontrol edin.\n", 
                        mimetype='application/x-mpegurl')

    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-name="{title}" group-title="YouTube Akışı",{title}\n'
        f'{stream_url}\n'
    )
    
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/')
def home():
    domain = request.host_url.strip('/')
    return (
        "<h1>YouTube'dan IPTV Akışı Proxy'si</h1>"
        "<h3>Örnek Kullanım:</h3>"
        f"<p><code>{domain}/dQw4w9WgXcQ</code></p>"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
