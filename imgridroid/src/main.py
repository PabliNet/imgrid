#!/usr/bin/env python3
"""
Imgridroid — versión Android de imgrid/qtimgrid, basada en el motor pyimgrid.

Flujo:
  - El usuario elige una imagen (manualmente, o la app la recibe vía
    "Compartir" / "Abrir con" desde otra app, ej. la Galería).
  - Se arma una copia reducida en cache para preview en vivo.
  - Al mover los sliders de columnas / filas / gap (o tocar el color de
    fondo), se recalcula el preview con pyimgrid sobre la copia chica.
  - Al tocar "Generar", se corre pyimgrid sobre la imagen a resolución
    completa, y el resultado se puede Compartir o Guardar.
"""
from os import makedirs
from os.path import join, basename, splitext
from shutil import copyfile
from threading import Thread

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import (
    BooleanProperty, ListProperty, NumericProperty, ObjectProperty,
    StringProperty,
)
from kivy.utils import platform

from pyimgrid import create_image

VERSION = '0.1.0'

# Tamaño máximo (lado mayor, en px) de la copia usada para el preview en
# vivo. No afecta la calidad del archivo final: "Generar" siempre corre
# sobre la imagen original a resolución completa.
PREVIEW_MAX_SIDE = 800

# Debounce (segundos) entre que el usuario mueve un slider y se recalcula
# el preview, para no recalcular en cada frame del drag.
PREVIEW_DEBOUNCE = 0.18

DEFAULT_BG_HEX = '#FFFFFF'


# ─────────────────────────────────────────────────────────────────────────
# Utilidades de idioma (mismo criterio que imgrid.py / qtimgrid.py)
# ─────────────────────────────────────────────────────────────────────────
def _detect_lang():
    if platform == 'android':
        try:
            from jnius import autoclass
            Locale = autoclass('java.util.Locale')
            return Locale.getDefault().getLanguage()
        except Exception:
            return 'en'
    from locale import getlocale, LC_ALL, setlocale
    try:
        setlocale(LC_ALL, '')
    except Exception:
        pass
    return (getlocale()[0] or 'en').split('_')[0]


LANG = _detect_lang()

MESSAGES = {
    'es': {
        'choose_image': 'Elegir imagen',
        'columns': 'Columnas',
        'rows': 'Filas',
        'gap': 'Separación',
        'bg_color': 'Color de fondo',
        'generate': 'Generar',
        'share': 'Compartir',
        'save': 'Guardar',
        'saved_ok': 'Imagen guardada en {path}',
        'save_error': 'No se pudo guardar la imagen.',
        'no_image': 'Primero elegí una imagen.',
        'generating': 'Generando…',
        'generated_ok': 'Imagen generada.',
        'generate_error': 'Error al generar la imagen.',
    },
    'en': {
        'choose_image': 'Choose image',
        'columns': 'Columns',
        'rows': 'Rows',
        'gap': 'Gap',
        'bg_color': 'Background color',
        'generate': 'Generate',
        'share': 'Share',
        'save': 'Save',
        'saved_ok': 'Image saved to {path}',
        'save_error': 'Could not save the image.',
        'no_image': 'Choose an image first.',
        'generating': 'Generating…',
        'generated_ok': 'Image generated.',
        'generate_error': 'Failed to generate the image.',
    },
}


def t(key: str) -> str:
    return MESSAGES.get(LANG, MESSAGES['en']).get(key, key)


# ─────────────────────────────────────────────────────────────────────────
# Helpers de almacenamiento Android (carpeta propia, fuera de DCIM)
# ─────────────────────────────────────────────────────────────────────────
def get_app_storage_dir() -> str:
    """Carpeta propia de la app para guardar resultados.

    En Android es Pictures/Imgridroid/ (visible al usuario vía un
    administrador de archivos o al compartir, pero separada de DCIM/Camera).
    En desktop (para probar sin Android) usa una carpeta local.
    """
    if platform == 'android':
        from android.storage import primary_external_storage_path  # noqa
        base = join(primary_external_storage_path(), 'Pictures', 'Imgridroid')
    else:
        base = join(App.get_running_app().user_data_dir, 'Imgridroid')
    makedirs(base, exist_ok=True)
    return base


def get_cache_dir() -> str:
    """Carpeta temporal propia de la app (no es responsabilidad de Imgridroid
    conservar lo que haya ahí entre sesiones)."""
    base = join(App.get_running_app().user_data_dir, 'cache')
    makedirs(base, exist_ok=True)
    return base


# ─────────────────────────────────────────────────────────────────────────
# Recepción de imágenes compartidas / "Abrir con" desde otras apps
# ─────────────────────────────────────────────────────────────────────────
def resolve_shared_uri_to_path(uri_str: str):
    """Copia el contenido de una content:// URI de Android a un archivo
    local en la cache propia de la app, y devuelve esa ruta local.

    Las URIs que entrega el Intent de "Compartir" pertenecen a la app que
    comparte y pueden dejar de ser válidas en cualquier momento, así que
    Imgridroid nunca trabaja directo sobre ellas: las copia una vez y usa
    siempre su propia copia.
    """
    if platform != 'android':
        return uri_str if uri_str else None

    try:
        from jnius import autoclass

        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        uri = Uri.parse(uri_str)

        input_stream = resolver.openInputStream(uri)
        dest_path = join(get_cache_dir(), 'shared_input.png')

        File = autoclass('java.io.File')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        out = FileOutputStream(File(dest_path))

        JByteArray = autoclass('[B')
        jbuf = JByteArray(8192)
        while True:
            n = input_stream.read(jbuf)
            if n == -1:
                break
            out.write(jbuf, 0, n)
        out.close()
        input_stream.close()

        return dest_path
    except Exception:
        return None


def share_file(path: str) -> None:
    """Dispara el Share Sheet de Android para el archivo generado."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass, cast

        Intent = autoclass('android.content.Intent')
        File = autoclass('java.io.File')
        FileProvider = autoclass('androidx.core.content.FileProvider')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity

        file_obj = File(path)
        authority = activity.getPackageName() + '.fileprovider'
        uri = FileProvider.getUriForFile(activity, authority, file_obj)

        intent = Intent(Intent.ACTION_SEND)
        intent.setType('image/png')
        intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        chooser = Intent.createChooser(intent, t('share'))
        activity.startActivity(chooser)
    except Exception as e:
        print(f'[Imgridroid] share_file error: {e}')


# ─────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────
KV = '''
BoxLayout:
    orientation: 'vertical'
    padding: dp(16)
    spacing: dp(12)

    Image:
        id: preview_image
        size_hint_y: 0.5
        fit_mode: 'contain'
        source: app.preview_source

    Button:
        text: app.tr('choose_image')
        size_hint_y: None
        height: dp(48)
        on_release: app.open_file_chooser()

    GridLayout:
        cols: 2
        size_hint_y: None
        height: dp(140)
        spacing: dp(8)

        Label:
            text: f"{app.tr('columns')}: {int(cols_slider.value)}"
        Slider:
            id: cols_slider
            min: 1
            max: 20
            value: app.cols
            step: 1
            on_value: app.on_param_change('cols', self.value)

        Label:
            text: f"{app.tr('rows')}: {int(rows_slider.value)}"
        Slider:
            id: rows_slider
            min: 1
            max: 20
            value: app.rows
            step: 1
            on_value: app.on_param_change('rows', self.value)

        Label:
            text: f"{app.tr('gap')}: {int(gap_slider.value)}px"
        Slider:
            id: gap_slider
            min: 0
            max: 100
            value: app.gap
            step: 1
            on_value: app.on_param_change('gap', self.value)

        Label:
            text: app.tr('bg_color')
        Button:
            text: app.bg_hex
            background_color: app.bg_rgba
            on_release: app.open_color_picker()

    Button:
        text: app.tr('generate')
        size_hint_y: None
        height: dp(52)
        on_release: app.generate_full()

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)

        Button:
            text: app.tr('share')
            disabled: not app.has_result
            on_release: app.on_share()

        Button:
            text: app.tr('save')
            disabled: not app.has_result
            on_release: app.on_save()

    Label:
        id: status_label
        text: app.status_text
        size_hint_y: None
        height: dp(30)
'''


class ImgridroidApp(App):
    title = 'Imgridroid'

    # Imagen original (resolución completa) ya resuelta a un path local.
    source_path = StringProperty('')
    # Copia reducida usada solo para preview en vivo.
    preview_source_path = StringProperty('')
    # Lo que efectivamente muestra el widget Image (preview del *resultado*
    # del grid, no de la imagen original).
    preview_source = StringProperty('')

    cols = NumericProperty(3)
    rows = NumericProperty(3)
    gap = NumericProperty(0)
    bg_hex = StringProperty(DEFAULT_BG_HEX)
    bg_rgba = ListProperty([1, 1, 1, 1])

    has_result = BooleanProperty(False)
    result_path = StringProperty('')
    status_text = StringProperty('')

    _debounce_ev = ObjectProperty(None, allownone=True)

    def tr(self, key: str) -> str:
        return t(key)

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        # Si la app fue abierta vía Intent (Compartir / Abrir con), Android
        # entrega la URI acá.
        self._handle_incoming_intent()

    # ── Recepción de imágenes desde otras apps ────────────────────────
    def _handle_incoming_intent(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            intent = activity.getIntent()
            action = intent.getAction()
            Intent = autoclass('android.content.Intent')

            uri = None
            if action == Intent.ACTION_SEND:
                extra_stream = intent.getParcelableExtra(Intent.EXTRA_STREAM)
                if extra_stream:
                    uri = extra_stream.toString()
            elif action == Intent.ACTION_VIEW:
                data = intent.getData()
                if data:
                    uri = data.toString()

            if uri:
                self._load_image_from_uri(uri)
        except Exception as e:
            print(f'[Imgridroid] _handle_incoming_intent error: {e}')

    def _load_image_from_uri(self, uri_str: str):
        local_path = resolve_shared_uri_to_path(uri_str)
        if local_path:
            self._set_source_image(local_path)

    # ── Selección manual de imagen ─────────────────────────────────────
    def open_file_chooser(self):
        # Usa plyer (incluido en buildozer.spec) para el selector nativo de
        # archivos. El callback corre en otro hilo, por eso se agenda en
        # el hilo principal de Kivy con Clock.
        try:
            from plyer import filechooser

            def _on_selection(selection):
                if selection:
                    Clock.schedule_once(
                        lambda dt: self._set_source_image(selection[0])
                    )

            filechooser.open_file(
                on_selection=_on_selection,
                filters=[('Images', '*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp')],
            )
        except Exception as e:
            self.status_text = t('save_error')
            print(f'[Imgridroid] open_file_chooser error: {e}')

    def _set_source_image(self, path: str):
        self.source_path = path
        self.preview_source = path  # mientras se genera la primer preview
        self._build_preview_copy(path)
        self._schedule_preview_update()

    def _build_preview_copy(self, path: str):
        """Genera una copia reducida (PREVIEW_MAX_SIDE) para que el recálculo
        en vivo del grid sea rápido sin importar el tamaño de la foto
        original."""
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as im:
                im.thumbnail((PREVIEW_MAX_SIDE, PREVIEW_MAX_SIDE))
                dest = join(get_cache_dir(), 'preview_source.png')
                im.save(dest)
                self.preview_source_path = dest
        except Exception as e:
            print(f'[Imgridroid] _build_preview_copy error: {e}')
            self.preview_source_path = path

    # ── Color de fondo ──────────────────────────────────────────────────
    def open_color_picker(self):
        from kivy.uix.colorpicker import ColorPicker
        from kivy.uix.popup import Popup

        picker = ColorPicker(color=self.bg_rgba)
        popup = Popup(title=t('bg_color'), content=picker, size_hint=(0.9, 0.9))

        def _on_color(_instance, value):
            self.bg_rgba = value
            r, g, b = (int(c * 255) for c in value[:3])
            self.bg_hex = f'#{r:02X}{g:02X}{b:02X}'
            self._schedule_preview_update()

        picker.bind(color=_on_color)
        popup.open()

    # ── Sliders: columnas / filas / gap ─────────────────────────────────
    def on_param_change(self, name: str, value):
        setattr(self, name, int(value))
        self._schedule_preview_update()

    def _schedule_preview_update(self):
        if not self.preview_source_path:
            return
        if self._debounce_ev is not None:
            self._debounce_ev.cancel()
        self._debounce_ev = Clock.schedule_once(
            lambda dt: self._run_preview_generation(), PREVIEW_DEBOUNCE
        )

    def _run_preview_generation(self):
        Thread(target=self._generate, args=(
            self.preview_source_path,
            join(get_cache_dir(), 'preview_output.png'),
            self._on_preview_ready,
        ), daemon=True).start()

    @mainthread
    def _on_preview_ready(self, ok: bool, out_path: str, _err):
        if ok:
            # Forzar a Kivy a recargar la imagen (mismo nombre de archivo).
            self.preview_source = ''
            self.preview_source = out_path

    # ── Generación final (resolución completa) ──────────────────────────
    def generate_full(self):
        if not self.source_path:
            self.status_text = t('no_image')
            return
        self.status_text = t('generating')
        name, _ext = splitext(basename(self.source_path))
        out_path = join(get_cache_dir(), f'{name}_{self.cols}x{self.rows}.png')
        Thread(target=self._generate, args=(
            self.source_path, out_path, self._on_full_ready,
        ), daemon=True).start()

    @mainthread
    def _on_full_ready(self, ok: bool, out_path: str, err):
        if ok:
            self.result_path = out_path
            self.has_result = True
            self.status_text = t('generated_ok')
        else:
            self.has_result = False
            self.status_text = t('generate_error')
            print(f'[Imgridroid] generate error: {err}')

    def _generate(self, src_path, dst_path, callback):
        """Corre pyimgrid.create_image fuera del hilo principal de Kivy."""
        try:
            create_image(
                src_path, dst_path,
                int(self.cols), int(self.rows),
                int(self.gap), self.bg_hex,
            )
            Clock.schedule_once(lambda dt: callback(True, dst_path, None))
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(False, dst_path, e))

    # ── Compartir / Guardar resultado ────────────────────────────────────
    def on_share(self):
        if not self.has_result:
            return
        share_file(self.result_path)

    def on_save(self):
        if not self.has_result:
            self.status_text = t('no_image')
            return
        try:
            dest_dir = get_app_storage_dir()
            dest_path = join(dest_dir, basename(self.result_path))
            copyfile(self.result_path, dest_path)
            self.status_text = t('saved_ok').format(path=dest_path)
        except Exception as e:
            self.status_text = t('save_error')
            print(f'[Imgridroid] on_save error: {e}')


if __name__ == '__main__':
    ImgridroidApp().run()
