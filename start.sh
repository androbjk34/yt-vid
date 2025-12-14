#!/bin/bash

# Node.js'nin PATH'e eklendiğinden emin ol
export PATH="/usr/bin/node:$PATH" 

# yt-dlp'nin Node.js'yi kullanması için ortam değişkeni ayarla
export YTDLP_EXTRA_OPTS="--js-runtimes node"

# Gunicorn'u başlat (Bu komut Python uygulamanızı çalıştırır)
gunicorn --bind 0.0.0.0:$PORT app:app
