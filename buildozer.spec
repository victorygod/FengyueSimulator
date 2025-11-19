[app]
title = 风月调试模拟器
package.name = FengyueSimulator
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js,txt

presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png

version = 0.1
requirements = python3,kivy,kivymd,plyer,requests,openssl

# Android 特定配置
android.permissions = INTERNET
android.api = 30
android.minapi = 21
android.sdk = 20
android.ndk = 19b

# 其他配置
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2

