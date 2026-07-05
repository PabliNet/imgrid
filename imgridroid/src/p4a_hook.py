"""
Hook de python-for-android para Imgridroid.

Se llama en before_apk_build, cuando el AndroidManifest.xml ya fue
renderizado desde el template pero Gradle todavía no lo compiló.
Hace dos cosas:
1. Inyecta el <provider> del FileProvider en el AndroidManifest.xml.
2. Copia file_paths.xml a res/xml/ para que el FileProvider pueda
   referenciarlo como @xml/file_paths.
"""
import os
import re
import shutil


def before_apk_build(ctx):
    manifest_path = os.path.join('src', 'main', 'AndroidManifest.xml')

    if not os.path.exists(manifest_path):
        print(f'[p4a_hook] ERROR: no se encontró {manifest_path}')
        return

    # ── 1. Copiar file_paths.xml a res/xml/ ──────────────────────────────
    res_xml_dir = os.path.join('src', 'main', 'res', 'xml')
    os.makedirs(res_xml_dir, exist_ok=True)
    src_file_paths = os.path.join(
        ctx.buildozer.root_dir, 'src', 'android_extra', 'file_paths.xml'
    )
    file_paths_dest = os.path.join(res_xml_dir, 'file_paths.xml')
    import shutil
    shutil.copy2(src_file_paths, file_paths_dest)
    print(f'[p4a_hook] file_paths.xml copiado a {file_paths_dest}')

    # ── 2. Inyectar <provider> en AndroidManifest.xml ────────────────────
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
