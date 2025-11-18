[app]
title = 风月调试模拟器
package.name = chatapp
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,html,css,js,txt

version = 0.1
requirements = python3,kivy,kivymd,plyer

[buildozer]
log_level = 2

[app]
presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png