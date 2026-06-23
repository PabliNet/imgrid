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

# Manifest completo personalizado: incluye FileProvider, intent-filters
# para "Compartir"/"Abrir con", y todos los permisos. Se usa en lugar de
# android.extra_manifest_application_arguments y
# android.manifest.intent_filters, que inyectan fragmentos XML via
# --extra-manifest-application-arguments de p4a — ese mecanismo pasa el
# contenido del archivo como string con \n literales en vez de saltos de
# línea reales, lo que rompe el parser XML del manifest merger de Gradle
# (ManifestMerger2$MergeFailureException).
android.manifest = src/android_extra/AndroidManifest.xml

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
