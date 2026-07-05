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

# Intent-filters para recibir imágenes compartidas / "Abrir con".
# p4a los inserta dentro de <activity> en el manifest — funciona
# correctamente porque el template ya tiene xmlns:android declarado.
android.manifest.intent_filters = src/android_extra/intent_filters.xml

# file_paths.xml va a res/xml/ (buildozer copia esto correctamente vía
# el flag --res_xml de python-for-android) para que el FileProvider
# pueda referenciarlo como @xml/file_paths.
android.res_xml = src/android_extra/file_paths.xml

# Hook que inyecta el <provider> del FileProvider en el manifest
# generado, en el momento before_apk_build (manifest ya renderizado,
# Gradle todavía no compiló). Esto reemplaza el paso de apktool en
# build.yml y permite publicar en F-Droid sin post-procesamiento.
p4a.hook = src/p4a_hook.py

android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.13.1

icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/icon.png

fullscreen = 0


[buildozer]
log_level = 2
warn_on_root = 1
