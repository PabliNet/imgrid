"""
Hook de python-for-android para Imgridroid.

Inyecta el <provider> del FileProvider en el AndroidManifest. Como el
orden exacto de renderizado del manifest puede variar según la versión
de python-for-android (algunas renderizan el manifest final DESPUÉS de
correr before_apk_build, pisando ediciones hechas sobre el XML ya
renderizado), este hook prueba TODAS las rutas y momentos posibles:

- before_apk_build: intenta parchear la plantilla Jinja2
  (templates/AndroidManifest.tmpl.xml) para que el <provider> sobreviva
  al re-render, y también el XML final por si ya existe.
- after_apk_build: vuelve a intentar sobre el XML final, por si el
  render ocurrió después de before_apk_build.

file_paths.xml se copia a res/xml/ automáticamente por buildozer/p4a
a través de la opción `android.res_xml` del buildozer.spec — no hace
falta (ni conviene) copiarlo manualmente acá.
"""
import os
import re


PROVIDER_XML = '''
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="org.imgrid.imgridroid.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>'''

CANDIDATE_PATHS = [
    os.path.join('templates', 'AndroidManifest.tmpl.xml'),
    os.path.join('src', 'main', 'AndroidManifest.tmpl.xml'),
    os.path.join('src', 'main', 'AndroidManifest.xml'),
]


def _patch_file(path, tag):
    if not os.path.exists(path):
        print(f'[p4a_hook][{tag}] no existe: {path}')
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'FileProvider' in content:
        print(f'[p4a_hook][{tag}] FileProvider ya presente en {path}, saltando.')
        return True

    patched = re.sub(r'(\s*</application>)', PROVIDER_XML + r'\1', content, count=1)

    if patched == content:
        print(f'[p4a_hook][{tag}] ERROR: no se encontró </application> en {path}.')
        return False

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print(f'[p4a_hook][{tag}] FileProvider inyectado en {path}')
    return True


def _patch_all(tag):
    print(f'[p4a_hook][{tag}] cwd={os.getcwd()}')
    any_ok = False
    for path in CANDIDATE_PATHS:
        if _patch_file(path, tag):
            any_ok = True
    if not any_ok:
        print(f'[p4a_hook][{tag}] ADVERTENCIA: ninguna ruta candidata funcionó.')


def before_apk_build(ctx):
    _patch_all('before_apk_build')


def after_apk_build(ctx):
    _patch_all('after_apk_build')
