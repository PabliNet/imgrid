"""
Hook de python-for-android para Imgridroid.

Se llama en before_apk_build, ANTES de que build.py renderice
src/main/AndroidManifest.xml a partir de la plantilla Jinja2
(templates/AndroidManifest.tmpl.xml dentro del dist_dir). Por eso
parcheamos la PLANTILLA y no el XML final: si patcheáramos el XML ya
renderizado, el siguiente render lo pisaría antes de que Gradle
compile.

file_paths.xml se copia a res/xml/ automáticamente por buildozer/p4a
a través de la opción `android.res_xml` del buildozer.spec — no hace
falta (ni conviene) copiarlo manualmente acá.
"""
import os
import re


def before_apk_build(ctx):
    # La plantilla vive en <dist_dir>/templates/. El cwd durante este
    # hook ya es el dist_dir.
    manifest_path = os.path.join('templates', 'AndroidManifest.tmpl.xml')

    if not os.path.exists(manifest_path):
        print(f'[p4a_hook] ERROR: no se encontró {manifest_path}')
        return

    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    provider = '''
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="org.imgrid.imgridroid.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>'''

    if 'FileProvider' in content:
        print('[p4a_hook] FileProvider ya presente, saltando.')
        return

    patched = re.sub(
        r'(\s*</application>)',
        provider + r'\1',
        content,
        count=1
    )

    if patched == content:
        print(f'[p4a_hook] ERROR: no se encontró </application> en {manifest_path}.')
        return

    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print(f'[p4a_hook] FileProvider inyectado en {manifest_path}')
