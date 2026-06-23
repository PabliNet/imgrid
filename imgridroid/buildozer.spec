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
android.minapi = 24
android.ndk_api = 24
android.archs = arm64-v8a,armeabi-v7a

# Acepta automáticamente las licencias del Android SDK en CI.
android.accept_sdk_license = True

# Permisos declarados también en el AndroidManifest.xml custom.
android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Hook de p4a: parchea el AndroidManifest.xml generado para agregar el
# <provider> del FileProvider. Es más confiable que
# extra_manifest_application_arguments (que pasa XML con \n literales
# rompiendo el parser de Gradle) y que android.manifest (que buildozer
# ignora silenciosamente — no existe como opción real de buildozer).
p4a.hook = src/p4a_hook.py

# file_paths.xml va a res/xml/ para que el FileProvider pueda
# referenciarlo como @xml/file_paths.
android.res_xml = src/android_extra/file_paths.xml

# Habilita AndroidX, requerido por androidx.core.content.FileProvider.
android.enable_androidx = True

# androidx.core debe declararse explícitamente.
android.gradle_dependencies = androidx.core:core:1.13.1

# Ícono.
icon.filename = %(source.dir)s/icon.png

fullscreen = 0


[buildozer]
log_level = 2
warn_on_root = 1
