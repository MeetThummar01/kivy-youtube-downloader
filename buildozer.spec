[app]
title = YouTube Downloader
package.name = ytloader
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3==3.9.18,kivy,yt-dlp,requests,pillow,pyjnius,setuptools,cython,docutils
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1
android.ndk = 25b
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
