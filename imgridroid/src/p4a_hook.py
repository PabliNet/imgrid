"""
Hook de python-for-android para Imgridroid.

Se llama en before_apk_build. IMPORTANTE: antes de que Gradle compile,
build.py vuelve a renderizar src/main/AndroidManifest.xml a partir de
la plantilla Jinja2 (templates/AndroidManifest.tmpl.xml dentro del
dist_dir), pisando cualquier edición hecha directamente sobre el XML
ya renderizado. Por eso este hook parchea la PLANTILLA, no el XML
final — así el <provider> sobrevive al re-render.

file_paths.xml se copia a res/xml/ automáticamente por buildozer/p4a
a través de la opción `android.res_xml` del buildozer.spec — no hace
falta (ni conviene) copiarlo manualmente acá.
"""
import os
import re


def before_apk_build(ctx):
    # La plantilla vive en <dist_dir>/templates/, no en src/main/.
    # El cwd durante este hook ya es el dist_dir.
    candidates = [
        os.path.join('templates', 'AndroidManifest.tmpl.xml'),
        os.path.join('src', 'main', 'AndroidManifest.tmpl.xml'),
    ]
    manifest_path = next((p for p in candidates if os.path.exists(p)), None)

    if manifest_path is None:
        print('[p4a_hook] ERROR: no se encontró AndroidManifest.tmpl.xml '
              f'en ninguna de estas rutas: {candidates}')
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

    print(f'[p4a_hook] FileProvider inyectado en la plantilla {manifest_path}')
