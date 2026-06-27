#!/usr/bin/env python3
"""
Imgridroid — versión Android de imgrid/qtimgrid, basada en el motor pyimgrid.

Flujo:
  - Al elegir imagen → se reduce una sola vez al tamaño del widget de
    preview y se guarda como copia de trabajo.
  - Generar → create_image trabaja sobre la copia reducida → preview rápida.
  - Guardar / Compartir → create_image sobre la original a resolución
    completa → solo cuando el usuario lo pide explícitamente.
"""
from os import makedirs
from os.path import join, basename, splitext
from shutil import copyfile
from threading import Thread

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import (
    BooleanProperty, ListProperty, NumericProperty,
    StringProperty,
)
from kivy.utils import platform

from pyimgrid import create_image

VERSION = '0.1.0'
DEFAULT_BG_HEX = '#FFFFFF'


# ─────────────────────────────────────────────────────────────────────────
# Idioma
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
        'bg_color': 'Fondo',
        'generate': 'Generar',
        'share': 'Compartir',
        'save': 'Guardar',
        'saved_ok': 'Imagen guardada.',
        'save_error': 'No se pudo guardar.',
        'no_image': 'Primero elegí una imagen.',
        'generating': 'Generando…',
        'generated_ok': '¡Listo!',
        'generate_error': 'Error al generar.',
        'preparing': 'Preparando imagen…',
        'saving_full': 'Generando en alta resolución…',
    },
    'en': {
        'choose_image': 'Choose image',
        'columns': 'Columns',
        'rows': 'Rows',
        'gap': 'Gap',
        'bg_color': 'Background',
        'generate': 'Generate',
        'share': 'Share',
        'save': 'Save',
        'saved_ok': 'Image saved.',
        'save_error': 'Could not save.',
        'no_image': 'Choose an image first.',
        'generating': 'Generating…',
        'generated_ok': 'Done!',
        'generate_error': 'Failed to generate.',
        'preparing': 'Preparing image…',
        'saving_full': 'Generating full resolution…',
    },
}


def t(key):
    return MESSAGES.get(LANG, MESSAGES['en']).get(key, key)


# ─────────────────────────────────────────────────────────────────────────
# Almacenamiento
# ─────────────────────────────────────────────────────────────────────────
def get_app_storage_dir():
    if platform == 'android':
        from android.storage import primary_external_storage_path
        base = join(primary_external_storage_path(), 'Pictures', 'Imgridroid')
    else:
        base = join(App.get_running_app().user_data_dir, 'Imgridroid')
    makedirs(base, exist_ok=True)
    return base


def get_cache_dir():
    base = join(App.get_running_app().user_data_dir, 'cache')
    makedirs(base, exist_ok=True)
    return base


# ─────────────────────────────────────────────────────────────────────────
# Permisos
# ─────────────────────────────────────────────────────────────────────────
def request_storage_permissions():
    if platform != 'android':
        return
    try:
        from android.permissions import request_permissions, Permission
        from jnius import autoclass
        Build = autoclass('android.os.Build$VERSION')
        if Build.SDK_INT >= 33:
            request_permissions([Permission.READ_MEDIA_IMAGES])
        else:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
    except Exception as e:
        print(f'[Imgridroid] request_storage_permissions: {e}')


# ─────────────────────────────────────────────────────────────────────────
# Intent entrante ("Compartir" / "Abrir con" desde otra app)
# ─────────────────────────────────────────────────────────────────────────
def resolve_shared_uri_to_path(uri_str):
    if platform != 'android':
        return uri_str or None
    try:
        from jnius import autoclass
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        resolver = activity.getContentResolver()
        uri = Uri.parse(uri_str)

        ext = '.png'
        try:
            MimeTypeMap = autoclass('android.webkit.MimeTypeMap')
            mime = resolver.getType(uri)
            if mime:
                detected = MimeTypeMap.getSingleton().getExtensionFromMimeType(mime)
                if detected:
                    ext = f'.{detected}'
        except Exception:
            pass

        input_stream = resolver.openInputStream(uri)
        dest_path = join(get_cache_dir(), f'shared_input{ext}')

        File = autoclass('java.io.File')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        out = FileOutputStream(File(dest_path))
        buf = bytearray(8192)
        while True:
            n = input_stream.read(buf, 0, len(buf))
            if n == -1:
                break
            out.write(buf, 0, n)
        out.close()
        input_stream.close()
        return dest_path
    except Exception as e:
        print(f'[Imgridroid] resolve_shared_uri_to_path: {e}')
        return None


# ─────────────────────────────────────────────────────────────────────────
# Compartir
# ─────────────────────────────────────────────────────────────────────────
def share_file(path, on_error=None):
    if platform != 'android':
        return
    try:
        from jnius import autoclass, cast

        Intent = autoclass('android.content.Intent')
        FileProvider = autoclass('androidx.core.content.FileProvider')
        File = autoclass('java.io.File')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity

        authority = activity.getPackageName() + '.fileprovider'
        uri = FileProvider.getUriForFile(activity, authority, File(str(path)))
        parcelable_uri = cast('android.os.Parcelable', uri)

        intent = Intent(Intent.ACTION_SEND)
        intent.setType('image/png')
        intent.putExtra(Intent.EXTRA_STREAM, parcelable_uri)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        ClipData = autoclass('android.content.ClipData')
        ClipDescription = autoclass('android.content.ClipDescription')
        ClipDataItem = autoclass('android.content.ClipData$Item')
        String = autoclass('java.lang.String')
        clip = ClipData(
            ClipDescription(String('image'), [String('image/png')]),
            ClipDataItem(uri)
        )
        intent.setClipData(clip)

        activity.startActivity(Intent.createChooser(intent, String(t('share'))))

    except Exception:
        import traceback
        msg = traceback.format_exc()
        print(f'[Imgridroid] share_file: {msg}')
        if on_error:
            on_error(msg)


# ─────────────────────────────────────────────────────────────────────────
# Reducir imagen al tamaño del widget de preview
# ─────────────────────────────────────────────────────────────────────────
def make_preview_copy(src_path, widget_w, widget_h):
    """Genera una sola vez una copia de la imagen reducida al tamaño del
    widget de preview. Esta copia se usa para todas las previews sucesivas
    — nunca se regenera desde la original al cambiar parámetros del grid.
    """
    try:
        from PIL import Image as PILImage
        with PILImage.open(src_path) as im:
            if im.width <= widget_w and im.height <= widget_h:
                return src_path
            im.thumbnail((int(widget_w), int(widget_h)), PILImage.LANCZOS)
            import hashlib
            tag = hashlib.md5(src_path.encode()).hexdigest()[:8]
            dest = join(get_cache_dir(), f'preview_copy_{tag}.png')
            im.save(dest)
            return dest
    except Exception as e:
        print(f'[Imgridroid] make_preview_copy: {e}')
        return src_path


# ─────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────
KV = '''
BoxLayout:
    orientation: 'vertical'
    padding: dp(12)
    spacing: dp(8)

    Image:
        id: preview_image
        size_hint_y: 0.5
        fit_mode: 'contain'
        source: app.result_image
        canvas.before:
            Color:
                rgba: 0, 0, 0, 1
            Rectangle:
                pos: self.pos
                size: self.size

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
        disabled: not app.source_path
        on_release: app.generate()

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
        text_size: self.width, None
        halign: 'left'
        valign: 'middle'
        height: max(dp(30), self.texture_size[1])
'''


class ImgridroidApp(App):
    title = 'Imgridroid'

    source_path      = StringProperty('')   # original a resolución completa
    preview_src_path = StringProperty('')   # copia reducida al tamaño del widget
    result_image     = StringProperty('')   # lo que muestra el widget Image

    cols    = NumericProperty(3)
    rows    = NumericProperty(3)
    gap     = NumericProperty(0)
    bg_hex  = StringProperty(DEFAULT_BG_HEX)
    bg_rgba = ListProperty([1, 1, 1, 1])

    has_result  = BooleanProperty(False)
    result_path = StringProperty('')   # resultado a resolución completa
    status_text = StringProperty('')

    def tr(self, key):
        return t(key)

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        request_storage_permissions()
        Clock.schedule_once(lambda dt: self._handle_incoming_intent(), 0.5)

    # ── Intent entrante ────────────────────────────────────────────────
    def _handle_incoming_intent(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            intent = PythonActivity.mActivity.getIntent()
            if intent is None:
                return
            Intent = autoclass('android.content.Intent')
            action = intent.getAction()
            uri = None
            if action == Intent.ACTION_SEND:
                extra = intent.getParcelableExtra(Intent.EXTRA_STREAM)
                if extra:
                    uri = extra.toString()
            elif action == Intent.ACTION_VIEW:
                data = intent.getData()
                if data:
                    uri = data.toString()
            if uri:
                local = resolve_shared_uri_to_path(uri)
                if local:
                    self._set_source(local)
        except Exception as e:
            print(f'[Imgridroid] _handle_incoming_intent: {e}')

    # ── Selección de imagen ────────────────────────────────────────────
    def open_file_chooser(self):
        try:
            from plyer import filechooser
            def _cb(sel):
                if sel:
                    Clock.schedule_once(lambda dt: self._set_source(sel[0]))
            filechooser.open_file(
                on_selection=_cb,
                filters=[('Images', '*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp')],
            )
        except Exception as e:
            self.status_text = str(e)

    def _set_source(self, path):
        self.source_path = path
        self.result_image = path
        self._invalidate_result()
        self.status_text = t('preparing')
        self._start_preview_copy()

    def _start_preview_copy(self):
        """Lanza la generación de la copia de trabajo en hilo secundario."""
        if not self.source_path:
            return
        widget = self.root.ids.preview_image
        w, h = widget.width, widget.height
        if w < 10 or h < 10:
            from kivy.core.window import Window
            w, h = Window.width, Window.height * 0.5
        Thread(
            target=self._prepare_preview_copy,
            args=(self.source_path, w, h),
            daemon=True,
        ).start()

    def _prepare_preview_copy(self, path, w, h):
        preview = make_preview_copy(path, w, h)
        Clock.schedule_once(lambda dt: self._on_preview_copy_ready(preview))

    @mainthread
    def _on_preview_copy_ready(self, preview_path):
        self.preview_src_path = preview_path
        self.status_text = ''

    # ── Parámetros ────────────────────────────────────────────────────
    def on_param_change(self, name, value):
        setattr(self, name, int(value))
        self._invalidate_result()

    def _invalidate_result(self):
        self.has_result = False

    # ── Color de fondo ────────────────────────────────────────────────
    def open_color_picker(self):
        from kivy.uix.colorpicker import ColorPicker
        from kivy.uix.popup import Popup
        picker = ColorPicker(color=self.bg_rgba)
        popup = Popup(title=t('bg_color'), content=picker, size_hint=(0.9, 0.9))
        def _on_color(_inst, value):
            self.bg_rgba = value
            r, g, b = (int(c * 255) for c in value[:3])
            self.bg_hex = f'#{r:02X}{g:02X}{b:02X}'
            self._invalidate_result()
        picker.bind(color=_on_color)
        popup.open()

    # ── Generar (preview rápida sobre copia reducida) ──────────────────
    def generate(self):
        if not self.source_path:
            self.status_text = t('no_image')
            return
        # Usar copia reducida si está lista, si no usar original
        src = self.preview_src_path or self.source_path
        self.status_text = t('generating')
        self.has_result = False
        name, _ = splitext(basename(self.source_path))
        bg = self.bg_hex.lstrip('#')
        out = join(get_cache_dir(),
                   f'{name}_{self.cols}x{self.rows}_g{self.gap}_{bg}.png')
        Thread(
            target=self._run_generate,
            args=(src, out),
            daemon=True,
        ).start()

    def _run_generate(self, src, dst):
        try:
            create_image(src, dst, int(self.cols), int(self.rows),
                         int(self.gap), self.bg_hex)
            Clock.schedule_once(lambda dt: self._on_done(True, dst, None))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_done(False, dst, e))

    @mainthread
    def _on_done(self, ok, path, err):
        if ok:
            self.result_path = path   # preview — se usa para compartir/guardar
            self.has_result = True
            self.status_text = t('generated_ok')
            self.result_image = ''
            self.result_image = path
        else:
            self.status_text = t('generate_error')
            print(f'[Imgridroid] generate error: {err}')

    # ── Compartir / Guardar (resolución completa) ──────────────────────
    def on_share(self):
        if not self.has_result:
            return
        self.status_text = t('saving_full')
        Thread(target=self._generate_full_then,
               args=('share',), daemon=True).start()

    def on_save(self):
        if not self.has_result:
            return
        self.status_text = t('saving_full')
        Thread(target=self._generate_full_then,
               args=('save',), daemon=True).start()

    def _generate_full_then(self, action):
        """Genera el resultado a resolución completa y luego comparte o guarda."""
        try:
            name, _ = splitext(basename(self.source_path))
            bg = self.bg_hex.lstrip('#')
            out = join(get_cache_dir(),
                       f'{name}_{self.cols}x{self.rows}_g{self.gap}_{bg}_full.png')
            create_image(self.source_path, out,
                         int(self.cols), int(self.rows),
                         int(self.gap), self.bg_hex)
            Clock.schedule_once(lambda dt: self._on_full_ready(action, out))
        except Exception as e:
            Clock.schedule_once(
                lambda dt: setattr(self, 'status_text', t('generate_error')))
            print(f'[Imgridroid] _generate_full_then: {e}')

    @mainthread
    def _on_full_ready(self, action, path):
        self.status_text = ''
        if action == 'share':
            share_file(path, on_error=self._show_share_error)
        elif action == 'save':
            try:
                dest = join(get_app_storage_dir(), basename(path))
                copyfile(path, dest)
                self.status_text = t('saved_ok')
            except Exception as e:
                self.status_text = t('save_error')
                print(f'[Imgridroid] on_save: {e}')

    def _show_share_error(self, msg):
        self.status_text = msg
        try:
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label
            label = Label(
                text=msg,
                text_size=(self.root.width * 0.9, None),
                size_hint=(1, None),
                halign='left',
                valign='top',
            )
            label.bind(texture_size=lambda inst, sz: setattr(inst, 'height', sz[1]))
            Popup(title='Error al compartir', content=label,
                  size_hint=(0.9, 0.7)).open()
        except Exception:
            pass


if __name__ == '__main__':
    ImgridroidApp().run()
