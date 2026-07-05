"""
Hook de python-for-android para Imgridroid.

Se llama en before_apk_build, cuando el AndroidManifest.xml ya fue
renderizado desde el template pero Gradle todavía no lo compiló.
Inyecta el <provider> del FileProvider directamente en el XML en texto
plano — el namespace xmlns:android ya está declarado en el documento
raíz, así que los atributos android: son válidos sin redeclararlo.

file_paths.xml se copia a res/xml/ automáticamente por buildozer/p4a
a través de la opción `android.res_xml` del buildozer.spec — no hace
falta (ni conviene) copiarlo manualmente acá.
"""
import os
import re


def before_apk_build(ctx):
    manifest_path = os.path.join('src', 'main', 'AndroidManifest.xml')

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
        print('[p4a_hook] ERROR: no se encontró </application>.')
        return

    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print(f'[p4a_hook] FileProvider inyectado en {manifest_path}')
