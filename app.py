import os
from flask import Flask, Response, request
import yt_dlp
from urllib.parse import urlparse, parse_qs

# Gunicorn'un bulması gereken Flask uygulaması (Değişken adı "app" olmalı!)
app = Flask(__name__)

# --- Yardımcı Fonksiyonlar ---

def get_youtube_id(url_or_id):
    """
    Hem tam URL'den hem de sadece video kimliğinden (ID) YouTube kimliğini çıkarır.
    """
    # Eğer doğrudan 11 karakterlik ID verilmişse
    if len(url_or_id) == 11 and all(c.isalnum() or c in '-_' for c in url_or_id):
        return url_or_id
    
    # Tam URL'den ID çıkarma
    try:
        parsed_url = urlparse(url_or_id)
        # URL parametrelerinden ID'yi çıkarma (e.g., /watch?v=ID)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
        # Kısa URL'den ID'yi çıkarma (e.g., youtu.be/ID)
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
    
    # yt-dlp seçenekleri
    ydl_opts = {
        # Yüksek kaliteli akışları tercih et (720p veya daha iyi)
        'format': 'bestvideo+bestaudio/best', 
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
        'retries': 5, 
    }
    
    stream_url = None
    title = f"YouTube Video ({youtube_id})"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            title = info_dict.get('title', title)
            
            # Doğrudan M3U8 veya MPD manifestosu arama (IPTV'lerin ihtiyacı olan)
            if info_dict.get('formats'):
                 for f in info_dict['formats']:
                    # HLS (M3U8) akışını arama - IPTV için en uygun format
                    if 'm3u8' in f.get('url', '') and f.get('protocol') in ('https', 'http'):
                        stream_url = f['url']
                        break
                    # DASH (MPD) akışını arama - M3U8 yoksa yedek
                    elif 'mpd' in f.get('url', '') and f.get('protocol') in ('https', 'http'):
                         stream_url = f['url']
            
            # Eğer özel bir manifest bulunamazsa, yt-dlp'nin en iyi seçimini kullan
            if not stream_url:
                stream_url = info_dict.get('url') 
            
            return stream_url, title
            
    except yt_dlp.DownloadError as e:
        print(f"yt-dlp Download Error: {e}")
        return None, title
    except Exception as e:
        print(f"Genel Hata: {e}")
        return None, title

# --- Flask Rotaları ---

@app.route('/<video_id_or_url>')
def generate_dynamic_m3u_playlist(video_id_or_url):
    """
    Verilen video ID'si/URL'si için M3U çalma listesi oluşturur.
    """
    # Gelen URL parametresini çözme (e.g. /https://www.youtube.com...)
    video_input = request.path.lstrip('/').replace('https:/', 'https://').replace('http:/', 'http://')
    
    youtube_id = get_youtube_id(video_input)

    if not youtube_id:
        return Response(f"#EXTM3U\n#ERROR: Geçersiz YouTube URL veya ID formatı.\n", 
                        mimetype='application/x-mpegurl', status=400)

    stream_url, title = get_stream_info(youtube_id)
    
    if not stream_url:
        return Response(f"#EXTM3U\n#ERROR: '{title}' videosu için yayın linki alınamadı. Bölgesel kısıtlama veya hata olabilir.\n", 
                        mimetype='application/x-mpegurl')

    # M3U içerik oluşturma
    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-name="{title}" group-title="YouTube Akışı",{title}\n'
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
        "<li><b>ID Kullanımı:</b> <code>[Domaininiz]/dQw4w9WgXcQ</code></li>"
        "<li><b>Tam URL Kullanımı:</b> <code>[Domaininiz]/https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></li>"
        "</ul>"
        "<p>Deneme videosu: <a href='/dQw4w9WgXcQ'>/dQw4w9WgXcQ</a></p>"
    )

if __name__ == '__main__':
    # Bu kısım sadece yerel çalıştırma için kullanılır, Gunicorn bu kısmı görmez.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
