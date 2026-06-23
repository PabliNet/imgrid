"""
Hook de python-for-android: inserta el <provider> del FileProvider en el
AndroidManifest.xml generado, justo antes del cierre de </application>.

Se ejecuta después de que p4a genera el manifest pero antes de que Gradle
lo compile. Esto evita los problemas de los mecanismos de inyección de
fragmentos XML de p4a (extra_manifest_application_arguments pasa el
contenido con \n literales, rompiendo el parser XML de Gradle).
"""
import os
import re


def hook(ctx):
    """Parchea el AndroidManifest.xml para agregar el FileProvider."""
    dist_dir = ctx.dist_dir
    manifest_path = os.path.join(
        dist_dir, 'src', 'main', 'AndroidManifest.xml'
    )

    if not os.path.exists(manifest_path):
        print(f'[hook] AndroidManifest.xml no encontrado en {manifest_path}')
        return

    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    provider_block = '''
        <!-- FileProvider para compartir archivos generados vía content:// URI -->
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="${applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>'''

    # Evitar insertar dos veces si el hook ya corrió
    if 'FileProvider' in content:
        print('[hook] FileProvider ya presente en el manifest, saltando.')
        return

    # Insertar antes del cierre de </application>
    patched = re.sub(
        r'(\s*</application>)',
        provider_block + r'\1',
        content,
        count=1
    )

    if patched == content:
        print('[hook] No se encontró </application> para parchear.')
        return

    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print(f'[hook] FileProvider insertado en {manifest_path}')
