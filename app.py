import os
from flask import Flask, Response, request
import yt_dlp
from urllib.parse import urlparse, parse_qs

# Gunicorn'un doğru bir şekilde bulması için Flask uygulamasının adı "app" olmalıdır.
app = Flask(__name__)

# --- Yardımcı Fonksiyonlar ---

def get_youtube_id(url_or_id):
    """
    Verilen string'den (tam URL veya sadece ID) geçerli bir YouTube video kimliği (ID) çıkarır.
    """
    # Gelen URL parametresini çözme (e.g. /https://www.youtube.com...)
    # Flask, '/' işaretini URL'nin parçası sanabilir. Bu satır, tam URL'leri düzeltir.
    processed_input = url_or_id.lstrip('/').replace('https:/', 'https://').replace('http:/', 'http://')
    
    # Eğer doğrudan 11 karakterlik ID verilmişse
    if len(processed_input) == 11 and all(c.isalnum() or c in '-_' for c in processed_input):
        return processed_input
    
    # Tam URL'den ID çıkarma
    try:
        parsed_url = urlparse(processed_input)
        
        # Standart URL'den ID çıkarma (e.g., /watch?v=ID)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
        # Kısa URL'den ID çıkarma (e.g., youtu.be/ID)
        elif parsed_url.hostname in ('youtu.be',):
            return parsed_url.path[1:]
    except Exception:
        pass
        
    return None # Geçersiz format

def get_stream_info(youtube_id):
    """
    yt-dlp kullanarak video bilgilerini ve doğrudan M3U8 akış URL'sini alır.
    IPTV uyumluluğu için HLS/DASH manifestolarına öncelik verir.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    
    ydl_opts = {
        # Video ve sesi birleştirmeyi zorla ve en iyi tek akışı dene
        'format': 'bestvideo[height<=720]+bestaudio/best', 
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True, 
        'retries': 5, 
        # Bölgesel kısıtlamaları aşmak için uygun bir user-agent kullan
        'outtmpl': '%(title)s.%(ext)s', 
    }
    
    stream_url = None
    title = f"YouTube Video ({youtube_id})"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            title = info_dict.get('title', title)
            
            # 1. Aşama: Tüm formatları gez ve HLS/DASH manifestolarına öncelik ver (IPTV uyumluluğu için)
            if info_dict.get('formats'):
                 for f in info_dict['formats']:
                    # HLS (M3U8) veya DASH (MPD) manifestosunu arama
                    if ('m3u8' in f.get('url', '') or f.get('ext') == 'm3u8') and f.get('protocol') in ('https', 'http'):
                        stream_url = f['url']
                        break
                    elif ('mpd' in f.get('url', '') or f.get('ext') == 'mpd') and f.get('protocol') in ('https', 'http'):
                         stream_url = f['url']
            
            # 2. Aşama: Eğer manifest bulunamazsa, yt-dlp'nin birleşik en iyi akışını kullan
            if not stream_url:
                stream_url = info_dict.get('url') 
                
            if stream_url and stream_url.startswith('http'):
                return stream_url, title
            
            return None, title
            
    except yt_dlp.DownloadError as e:
        # Hata yakalandığında loglara bas
        print(f"yt-dlp Download Error: {e}") 
        return None, title
    except Exception as e:
        print(f"Genel Hata: {e}")
        return None, title

# --- Flask Rotaları ---

@app.route('/<path:video_id_or_url>')
def generate_dynamic_m3u_playlist(video_id_or_url):
    """
    Kullanıcının verdiği video ID'si/URL'si için M3U çalma listesi oluşturur.
    """
    # 'path:video_id_or_url' kullanarak tam URL'nin sorunsuz geçmesini sağla
    youtube_id = get_youtube_id(video_id_or_url)

    if not youtube_id:
        return Response(f"#EXTM3U\n#ERROR: Geçersiz YouTube URL veya ID formatı. Kullanım: /dQw4w9WgXcQ veya /https://...\n", 
                        mimetype='application/x-mpegurl', status=400)

    stream_url, title = get_stream_info(youtube_id)
    
    if not stream_url:
        return Response(f"#EXTM3U\n#ERROR: '{title}' videosu için yayın linki alınamadı. (ID: {youtube_id}). Akış manifestosu bulunamadı.\n", 
                        mimetype='application/x-mpegurl')

    # M3U içerik oluşturma
    # Not: Bazı IPTV oynatıcıları, stream_url'nin tek bir M3U8 akışı olmasını bekler. 
    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-name="{title}" group-title="YouTube Akışı",{title}\n'
        f'{stream_url}\n'
    )
    
    # IPTV oynatıcılarının anlayacağı formatta yanıt döndür
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/')
def home():
    """
    Kullanım kılavuzu ve hoş geldiniz sayfası.
    """
    domain = request.host_url.strip('/')
    return (
        "<h1>YouTube'dan IPTV Akışı Proxy'si</h1>"
        "<h2>Kullanım Şekli:</h2>"
        "<p>IPTV oynatıcınızda çalma listesi URL'si olarak şunu kullanın:</p>"
        "<code>[Domaininiz]/[YouTube_Video_ID_veya_Tam_URL]</code>"
        "<h3>Örnekler:</h3>"
        "<ul>"
        f"<li><b>ID Kullanımı:</b> <code>{domain}/dQw4w9WgXcQ</code></li>"
        f"<li><b>Tam URL Kullanımı:</b> <code>{domain}/https://www.youtube.com/watch?v=dQw4w9WgXcQ</code></li>"
        "</ul>"
    )

if __name__ == '__main__':
    # Yerel geliştirme için kullanılır. Railway Gunicorn'u kullanır.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
