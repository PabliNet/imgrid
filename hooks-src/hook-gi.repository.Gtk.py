"""
PyInstaller hook — GTK4 + dependencias de sistema.

Copia al bundle:
  - Los typelibs necesarios (gi_typelibs/)
  - Las shared libraries de GTK4 y su cadena de dependencias
"""

from pathlib import Path
import subprocess
from PyInstaller.utils.hooks import collect_data_files

# ── Typelibs ──────────────────────────────────────────────────────────────────
TYPELIBS = [
    'Gtk-4.0',
    'Gdk-4.0',
    'Gio-2.0',
    'GLib-2.0',
    'GObject-2.0',
    'GModule-2.0',
    'GdkPixbuf-2.0',
    'Pango-1.0',
    'PangoCairo-1.0',
    'cairo-1.0',
    'Graphene-1.0',
    'HarfBuzz-0.0',
    'Gsk-4.0',
]

datas = []
typelib_dirs = [
    Path('/usr/lib/x86_64-linux-gnu/girepository-1.0'),
    Path('/usr/lib/girepository-1.0'),
]
for name in TYPELIBS:
    for d in typelib_dirs:
        f = d / f'{name}.typelib'
        if f.exists():
            datas.append((str(f), 'gi_typelibs'))
            break

# ── Shared libraries ──────────────────────────────────────────────────────────
SOLIBS = [
    'libgtk-4.so.1',
    'libgdk_pixbuf-2.0.so.0',
    'libpangocairo-1.0.so.0',
    'libpango-1.0.so.0',
    'libpangoft2-1.0.so.0',
    'libcairo.so.2',
    'libcairo-gobject.so.2',
    'libharfbuzz.so.0',
    'libharfbuzz-subset.so.0',
    'libfribidi.so.0',
    'libfontconfig.so.1',
    'libfreetype.so.6',
    'libgraphene-1.0.so.0',
    'libepoxy.so.0',
    'libpixman-1.so.0',
    'libxkbcommon.so.0',
    'libwayland-client.so.0',
    'libwayland-egl.so.1',
    'libX11.so.6',
    'libXi.so.6',
    'libXext.so.6',
    'libXcursor.so.1',
    'libXdamage.so.1',
    'libXfixes.so.3',
    'libXrandr.so.2',
    'libXinerama.so.1',
    'libXrender.so.1',
    'libXau.so.6',
    'libXdmcp.so.6',
    'libxcb.so.1',
    'libxcb-render.so.0',
    'libxcb-shm.so.0',
    'libpng16.so.16',
    'libtiff.so.6',
    'libjpeg.so.62',
    'libwebp.so.7',
    'libzstd.so.1',
    'libLerc.so.4',
    'libjbig.so.0',
    'libdeflate.so.0',
    'liblzo2.so.2',
    'libthai.so.0',
    'libdatrie.so.1',
    'libgraphite2.so.3',
    'libbrotlidec.so.1',
    'libbrotlicommon.so.1',
    'libsharpyuv.so.0',
    'libcloudproviders.so.0',
    'libexpat.so.1',
]

SO_DIRS = [
    Path('/lib/x86_64-linux-gnu'),
    Path('/usr/lib/x86_64-linux-gnu'),
]

binaries = []
for lib in SOLIBS:
    for d in SO_DIRS:
        f = d / lib
        if f.exists():
            binaries.append((str(f), '.'))
            break
    else:
        # ldconfig fallback
        try:
            result = subprocess.run(
                ['ldconfig', '-p'],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if lib in line and '=>' in line:
                    path = line.split('=>')[-1].strip()
                    if Path(path).exists():
                        binaries.append((path, '.'))
                        break
        except Exception:
            pass
