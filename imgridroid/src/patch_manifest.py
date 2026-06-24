"""
Parchea el AndroidManifest.xml desempaquetado por apktool para agregar:
1. Intent-filters SEND/VIEW para que Imgridroid aparezca en "Compartir"
2. FileProvider con meta-data para compartir archivos generados

Uso: python3 patch_manifest.py <path/to/AndroidManifest.xml>
"""
import sys
import re

path = sys.argv[1]
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f'[patch] Manifest original ({len(content)} bytes):')
print(content[:500])

# Intent-filters para SEND y VIEW (van dentro de <activity>)
intent_filters = '''
        <intent-filter>
            <action android:name="android.intent.action.SEND" />
            <category android:name="android.intent.category.DEFAULT" />
            <data android:mimeType="image/*" />
        </intent-filter>
        <intent-filter>
            <action android:name="android.intent.action.VIEW" />
            <category android:name="android.intent.category.DEFAULT" />
            <category android:name="android.intent.category.BROWSABLE" />
            <data android:mimeType="image/*" />
        </intent-filter>'''

# FileProvider (va dentro de <application>, fuera de <activity>)
file_provider = '''
        <provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="org.imgrid.imgridroid.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            <meta-data
                android:name="android.support.FILE_PROVIDER_PATHS"
                android:resource="@xml/file_paths" />
        </provider>'''

patched = content

if 'android.intent.action.SEND' not in patched:
    patched = re.sub(r'(\s*</activity>)', intent_filters + r'\1', patched, count=1)
    print('[patch] Intent-filters insertados OK')
else:
    print('[patch] Intent-filters ya presentes')

if 'FileProvider' not in patched:
    patched = re.sub(r'(\s*</application>)', file_provider + r'\1', patched, count=1)
    print('[patch] FileProvider insertado OK')
else:
    print('[patch] FileProvider ya presente')

with open(path, 'w', encoding='utf-8') as f:
    f.write(patched)

print('[patch] Manifest parcheado guardado')
print(f'[patch] Contenido final ({len(patched)} bytes):')
print(patched[-800:])
