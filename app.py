import os
from flask import Flask, Response
import yt_dlp

app = Flask(__name__)

# Örnek bir YouTube URL'si.
# Bunu kendi videonuzla değiştirin!
# Dikkat: Bu kod, yalnızca canlı yayınlar veya VOD'lar için M3U8 linkleri sağlayan videolarla çalışır.
YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 
CHANNEL_NAME = "Rick Astley Resmi Kanalı"
TITLE = "Never Gonna Give You Up"

def get_m3u8_url(youtube_url):
    """
    yt-dlp kullanarak YouTube videosunun doğrudan M3U8 akış URL'sini alır.
    """
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            # Eğer M3U8 akış URL'si mevcutsa onu kullanır.
            # Bazı formatlar (örneğin DASH) doğrudan IPTV oynatıcılarda çalışmayabilir.
            # 'hls' formatına öncelik vermeye çalışalım.
            m3u8_url = next(
                (f['url'] for f in info_dict.get('formats', []) if f.get('ext') == 'mp4' and f.get('protocol') == 'https'),
                info_dict.get('url') # Yedek olarak ana URL'yi kullan
            )
            return m3u8_url
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None

@app.route('/playlist')
def generate_m3u_playlist():
    """
    M3U formatında çalma listesi oluşturur.
    """
    stream_url = get_m3u8_url(YOUTUBE_URL)
    
    if not stream_url:
        return Response("#EXTM3U\n# YAYIN ALINAMADI\n", mimetype='application/x-mpegurl')

    m3u_content = (
        "#EXTM3U\n"
        f'#EXTINF:-1 tvg-id="{CHANNEL_NAME}" tvg-name="{CHANNEL_NAME}" group-title="YouTube",'
        f'{TITLE}\n'
        f'{stream_url}\n'
    )
    
    # IPTV oynatıcılarının anlayacağı M3U dosyasını döndürür.
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/')
def home():
    """
    Basit karşılama sayfası.
    """
    return (
        "<h1>YouTube'dan IPTV Akışı</h1>"
        "<p>M3U çalma listenizi almak için: <a href='/playlist'>/playlist</a></p>"
        "<p>Bu URL'yi IPTV oynatıcınıza ekleyin: (Railway domaininiz)/playlist</p>"
    )

if __name__ == '__main__':
    # Railway'de PORT ortam değişkenini kullanır.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
