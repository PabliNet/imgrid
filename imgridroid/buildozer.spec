[app]

title = Imgridroid
package.name = imgridroid
package.domain = org.imgrid

source.dir = src
source.include_exts = py,png,jpg,jpeg,kv,atlas

version = 0.1.0

requirements = python3,kivy==2.3.1,pillow,pyimgrid,plyer,pyjnius

# Orientación libre (la app funciona igual en vertical/horizontal).
orientation = portrait,landscape

# ── Android ────────────────────────────────────────────────────────────
android.api = 34
android.minapi = 23
android.ndk_api = 23
android.archs = arm64-v8a,armeabi-v7a

# Acepta automáticamente las licencias del Android SDK. Necesario para que
# el build corra sin intervención manual en GitHub Actions (sin esto,
# buildozer pregunta "Accept? (y/N)" de forma interactiva y, en CI, eso
# se interpreta como "no" — se saltea la instalación de build-tools y el
# build falla más adelante por falta de aidl).
android.accept_sdk_license = True

# Permisos:
#  - READ_MEDIA_IMAGES (Android 13+) / READ_EXTERNAL_STORAGE (Android <13):
#    necesarios para que el usuario elija una imagen manualmente.
#  - WRITE_EXTERNAL_STORAGE: solo relevante en Android <10, se mantiene
#    por compatibilidad con dispositivos viejos.
android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Copia file_paths.xml a res/xml/ para que el FileProvider declarado en
# file_provider.xml pueda referenciarlo como @xml/file_paths.
android.res_xml = src/android_extra/file_paths.xml

# FileProvider: necesario para compartir el resultado generado con otras
# apps (WhatsApp, Telegram, apps de impresoras, etc.) vía content:// URI
# en lugar de file:// (Android 7+ lo exige). Esto inyecta el <provider>
# dentro de <application> en el AndroidManifest.xml generado.
android.extra_manifest_application_arguments = src/android_extra/file_provider.xml

# Intent filters extra: hacen que Imgridroid aparezca como destino de
# "Compartir" y "Abrir con" cuando el usuario interactúa con una imagen
# desde la Galería u otra app. Esto inyecta <intent-filter> dentro de
# <activity> en el AndroidManifest.xml generado.
android.manifest.intent_filters = src/android_extra/intent_filters.xml

# Habilita AndroidX, requerido por androidx.core.content.FileProvider.
android.enable_androidx = True

# Ícono y splash (reemplazar por los assets reales del proyecto).
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

fullscreen = 0


[buildozer]
log_level = 2
warn_on_root = 1
