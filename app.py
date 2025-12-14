import os
from flask import Flask, Response, request
import yt_dlp
from urllib.parse import urlparse, parse_qs

# CRITICAL: Gunicorn'un bulması için değişken adı "app" olmalı.
app = Flask(__name__)

# --- Yardımcı Fonksiyonlar ---

def get_stream_info(url):
    """
    yt-dlp kullanarak verilen tam URL'den video akış URL'sini ve başlığını alır.
    """
    ydl_opts = {
        # En iyi formatı almayı dener. OK.ru için genellikle doğrudan link döndürür.
        'format': 'best', 
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True, 
        'retries': 5, 
        'outtmpl': '%(title)s.%(ext)s', 
        
        # User-Agent kısıtlamalarını aşmaya yardımcı olur.
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
    }
    
    stream_url = None
    title = "Harici Video Akışı"

    try:
        # YTDLP_EXEC ortam değişkeni (Railway'de ayarlanan) sayesinde JS runtime bulunacaktır.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Doğrudan tam URL'yi veriyoruz
            info_dict = ydl.extract_info(url, download=False)
            
            # Eğer başlık yoksa URL'yi başlık olarak kullan
            title = info_dict.get('title', url)
            
            # yt-dlp'nin bulduğu en iyi URL'yi kullan
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
    """
    Gelen tam URL'yi alır ve doğrudan yt-dlp'ye göndererek M3U akışı oluşturur.
    """
    # Gelen URL parametresini çözme ve düzeltme:
    # örn: /https:/ok.ru... -> https://ok.ru...
    video_input = video_id_or_url.lstrip('/').replace('https:/', 'https://').replace('http:/', 'http://')
    
    if not video_input.startswith(('http://', 'https://')):
        # Eğer gelen string bir URL değilse, kullanıcıya hata mesajı göster
        return Response(f"#EXTM3U\n#ERROR: Lütfen tam ve geçerli bir URL (http:// veya https:// ile başlayan) girin.\n", 
                        mimetype='application/x-mpegurl', status=400)
    
    # Tam URL'yi get_stream_info'ya gönderiyoruz
    stream_url, title = get_stream_info(video_input)
    
    if not stream_url:
        return Response(f"#EXTM3U\n#ERROR: '{title}' videosu için yayın linki ALINAMADI. Lütfen URL'yi kontrol edin.\n", 
                        mimetype='application/x-mpegurl')

    # M3U içerik oluşturma
    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-name="{title}" group-title="Harici Akış",{title}\n'
        f'{stream_url}\n'
    )
    
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/')
def home():
    """
    Kullanım kılavuzu ve hoş geldiniz sayfası.
    """
    domain = request.host_url.strip('/')
    return (
        "<h1>Harici Video Akış Proxy'si (OK.ru, YouTube vb.)</h1>"
        "<h2>Kullanım Şekli:</h2>"
        "<p>IPTV oynatıcınızda çalma listesi URL'si olarak şunu kullanın:</p>"
        "<code>[Domaininiz]/[Tam_Video_URL'si]</code>"
        "<h3>Örnek:</h3>"
        f"<li><b>OK.ru Kullanımı:</b> <code>{domain}/https://ok.ru/videoembed/7041299057281</code></li>"
        f"<li><b>YouTube Kullanımı:</b> <code>{domain}/https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></li>"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

