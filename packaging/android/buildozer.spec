# Beat Clap Android build. Run packaging/build-apk.sh rather than buildozer directly:
# it stages src/ (the game package + main.py), the icon, and fills in the version.
[app]
title = Beat Clap
package.name = beatclap
package.domain = org.beatclap
source.dir = src
source.include_exts = py,npz
version = @VERSION@
requirements = python3,pygame,numpy,pyjnius,android
icon.filename = icon.png
presplash.filename = presplash.png
android.presplash_color = #0E111E
orientation = landscape
fullscreen = 1
android.permissions = RECORD_AUDIO
android.api = 35
android.minapi = 29
android.ndk_api = 29
android.ndk = 28c
android.accept_sdk_license = True
android.archs = arm64-v8a
android.allow_backup = True
p4a.bootstrap = sdl2
p4a.branch = master
p4a.commit = v2026.05.09
p4a.local_recipes = ./p4a-recipes

[buildozer]
log_level = 2
warn_on_root = 1
