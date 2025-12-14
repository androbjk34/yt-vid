# app.py dosyasındaki get_stream_info fonksiyonunu bununla değiştirin:

def get_stream_info(youtube_id):
    """
    yt-dlp kullanarak video bilgilerini ve doğrudan M3U8 akış URL'sini alır.
    HLS veya MPEG-DASH akışlarına öncelik verir.
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    
    # yt-dlp seçenekleri
    ydl_opts = {
        # Sadece M3U8 (HLS) veya DASH manifestosu içeren formatları ara
        # Bu, çoğu IPTV oynatıcısının beklediği Adaptive Stream formatıdır.
        'format': 'best[protocol=http]', # Genel olarak en iyi HTTP tabanlı formatı deneme
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
        'forceurl': True, # Sadece URL'yi döndür
        'retries': 5, # Bağlantı hatalarına karşı deneme
    }
    
    stream_url = None
    title = f"YouTube Video ({youtube_id})"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video bilgilerini indirmeden çek
            info_dict = ydl.extract_info(url, download=False)
            
            title = info_dict.get('title', title)
            
            # 1. Aşama: Doğrudan akış URL'sini kontrol et (yt-dlp'nin en iyi seçimini kullan)
            stream_url = info_dict.get('url')
            
            # 2. Aşama: Eğer bir DASH manifestosu varsa (genellikle .mpd veya .m3u8), onu dene
            # Özellikle canlı yayınlarda veya bazı VOD'larda bu gereklidir.
            if info_dict.get('formats'):
                 for f in info_dict['formats']:
                    # HLS (M3U8) akışını arama
                    if 'm3u8' in f.get('url', '') and f.get('protocol') == 'https':
                        stream_url = f['url']
                        break
                    # DASH (MPD) akışını arama
                    elif 'mpd' in f.get('url', '') and f.get('protocol') == 'https':
                         # Bazı oynatıcılar MPD'yi desteklemediği için HLS'yi tercih ederiz,
                         # ancak HLS yoksa MPD bir yedektir.
                         stream_url = f['url']
                         break
            
            if stream_url:
                # Bazen yt-dlp, indirilebilir bir URL döndürür. Biz oynatılabilir bir URL istiyoruz.
                # Tekrar kontrol ediyoruz ve son M3U8 linkini döndürmeye çalışıyoruz.
                return stream_url, title
            
            # Eğer yukarıdaki yöntemlerle bulunamazsa, hata döndürülür
            return None, title
            
    except yt_dlp.DownloadError as e:
        print(f"yt-dlp Download Error: {e}")
        # Bu genellikle YouTube'un videonun akışını reddetmesi anlamına gelir.
        return None, title
    except Exception as e:
        print(f"Genel Hata: {e}")
        return None, title

# Diğer tüm kodlar (Flask rotaları, home() ve if __name__ == '__main__':) aynı kalacak.
