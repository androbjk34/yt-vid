import os
from flask import Flask, Response, request
import yt_dlp
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# --- Yardımcı Fonksiyonlar ---

def get_youtube_id(url_or_id):
    """
    Hem tam URL'den hem de sadece video kimliğinden (ID) YouTube kimliğini çıkarır.
    """
    # Eğer doğrudan ID verilmişse
    if len(url_or_id) == 11 and all(c.isalnum() or c in '-_' for c in url_or_id):
        return url_or_id
    
    # Tam URL'den ID çıkarma
    try:
        parsed_url = urlparse(url_or_id)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
        elif parsed_url.hostname in ('youtu.be',):
            return parsed_url.path[1:]
    except Exception:
        pass
        
    return None # Geçersiz format

def get_stream_info(youtube_id):
    """
    yt-dlp kullanarak video bilgilerini ve doğrudan M3U8 akış URL'sini alır.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]', # Daha hızlı yükleme için 720p'ye öncelik
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            # En iyi akış URL'sini bul
            stream_url = info_dict.get('url') # Ana URL veya en iyi formatın URL'si
            title = info_dict.get('title', f"YouTube Video ({youtube_id})")
            
            return stream_url, title
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None, None

# --- Flask Rotaları ---

@app.route('/<video_id_or_url>')
def generate_dynamic_m3u_playlist(video_id_or_url):
    """
    Kullanıcının verdiği video ID'si/URL'si için M3U çalma listesi oluşturur.
    """
    # URL veya ID'den temiz YouTube kimliğini al
    youtube_id = get_youtube_id(video_id_or_url)

    if not youtube_id:
        return Response(f"#EXTM3U\n#ERROR: Geçersiz YouTube URL veya ID formatı.\n", 
                        mimetype='application/x-mpegurl', status=400)

    stream_url, title = get_stream_info(youtube_id)
    
    if not stream_url:
        return Response(f"#EXTM3U\n#ERROR: '{title}' videosu için yayın linki alınamadı.\n", 
                        mimetype='application/x-mpegurl')

    # M3U içerik oluşturma
    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-name="{title}" group-title="YouTube Dinamik Akış",'
        f'{title}\n'
        f'{stream_url}\n'
    )
    
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/')
def home():
    """
    Kullanım kılavuzu.
    """
    return (
        "<h1>YouTube'dan IPTV Akışı</h1>"
        "<p>Bu servisi kullanarak istediğiniz YouTube videosunu IPTV oynatıcınıza ekleyebilirsiniz.</p>"
        "<h2>Kullanım Şekli:</h2>"
        "<p>IPTV oynatıcınızda çalma listesi URL'si olarak şunu kullanın:</p>"
        "<code>[Railway Domaininiz]/[YouTube_Video_ID_veya_Tam_URL]</code>"
        "<h3>Örnekler:</h3>"
        "<ul>"
        "<li><b>ID Kullanımı:</b> <code>[Railway Domaininiz]/dQw4w9WgXcQ</code></li>"
        "<li><b>Tam URL Kullanımı:</b> <code>[Railway Domaininiz]/https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></li>"
        "</ul>"
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
