[app]

title = Imgridroid
package.name = imgridroid
package.domain = org.imgrid

source.dir = src
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 0.2.0

requirements = python3,kivy==2.3.1,pillow,pyimgrid,plyer,pyjnius

orientation = portrait

# ── Android ────────────────────────────────────────────────────────────
android.api = 34
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a,armeabi-v7a

android.accept_sdk_license = True

android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# file_paths.xml va a res/xml/ para que el FileProvider pueda
# referenciarlo como @xml/file_paths. El <provider> se inyecta en el
# manifest vía apktool + patch_manifest.py en el build.yml (no desde
# buildozer, que no tiene un mecanismo confiable para esto).
android.res_xml = src/android_extra/file_paths.xml

android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.13.1

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png

fullscreen = 0


[buildozer]
log_level = 2
warn_on_root = 1
