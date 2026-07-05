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
from time import time
from os import makedirs
from os.path import join, basename, splitext
from shutil import copyfile
from threading import Thread

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import (
    BooleanProperty, ListProperty, NumericProperty,
    ObjectProperty, StringProperty,
)
from kivy.utils import platform

from pyimgrid import create_image

VERSION = '0.2.0'
DEFAULT_BG_HEX = None   # None = transparente (se pasa directo a create_image)


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
        'choose_image': 'Cargar imagen',
        'clipboard': 'Portapapeles',
        'clipboard_preview': '¿Importar esta imagen?',
        'import': 'Importar',
        'discard': 'Descartar',
        'clipboard_empty': 'No hay imagen en el portapapeles.',
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
        'choose_image': 'Load image',
        'clipboard': 'Clipboard',
        'clipboard_preview': 'Import this image?',
        'import': 'Import',
        'discard': 'Discard',
        'clipboard_empty': 'No image in clipboard.',
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

        # ─── Nombre único por timestamp ───────────────────────────────────
        # Esto obliga a Kivy a ignorar su caché de texturas y recargar la UI.
        timestamp = int(time() * 1000)
        dest_path = join(get_cache_dir(), f'shared_input_{timestamp}{ext}')
        # ─────────────────────────────────────────────────────────────────

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

    BoxLayout:
        size_hint_y: 0.5
        opacity: 1 if app.result_image else 0
        canvas.before:
            Color:
                rgba: 0, 0, 0, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Image:
            id: preview_image
            fit_mode: 'contain'
            source: app.result_image
            on_size: app.on_preview_widget_size(*self.size)

    BoxLayout:
        size_hint_y: None
        height: dp(48)
        spacing: dp(8)
        Button:
            text: app.tr('choose_image')
            on_release: app.open_file_chooser()
        Button:
            text: app.tr('clipboard')
            on_release: app.open_clipboard()

    # ── Columnas ──────────────────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: dp(36)
        spacing: dp(8)
        Label:
            text: app.tr('columns')
            size_hint_x: None
            width: dp(110)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Slider:
            id: cols_slider
            min: 1
            max: 10
            value: app.cols
            step: 1
            on_value: app.on_param_change('cols', self.value)
        Label:
            text: str(int(cols_slider.value))
            size_hint_x: None
            width: dp(30)
            halign: 'right'
            valign: 'middle'
            text_size: None, self.height

    # ── Filas ─────────────────────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: dp(36)
        spacing: dp(8)
        Label:
            text: app.tr('rows')
            size_hint_x: None
            width: dp(110)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Slider:
            id: rows_slider
            min: 1
            max: 10
            value: app.rows
            step: 1
            on_value: app.on_param_change('rows', self.value)
        Label:
            text: str(int(rows_slider.value))
            size_hint_x: None
            width: dp(30)
            halign: 'right'
            valign: 'middle'
            text_size: None, self.height

    # ── Separación ────────────────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: dp(36)
        spacing: dp(8)
        Label:
            text: app.tr('gap')
            size_hint_x: None
            width: dp(110)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Slider:
            id: gap_slider
            min: 0
            max: 35
            value: app.gap
            step: 1
            on_value: app.on_param_change('gap', self.value)
        Label:
            text: f"{int(gap_slider.value)}px"
            size_hint_x: None
            width: dp(40)
            halign: 'right'
            valign: 'middle'
            text_size: None, self.height

    # ── Fondo ─────────────────────────────────────────────────────────
    BoxLayout:
        size_hint_y: None
        height: dp(36)
        spacing: dp(8)
        Label:
            text: app.tr('bg_color')
            size_hint_x: None
            width: dp(110)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Button:
            text: app.bg_hex if app.bg_hex else 'Transparente'
            background_color: app.bg_rgba if app.bg_hex else (0.3, 0.3, 0.3, 1)
            on_release: app.open_color_picker()
        Button:
            text: '\u2715'
            size_hint_x: None
            width: dp(36)
            on_release: app.reset_bg_color()

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
        halign: 'center'
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
    bg_hex  = ObjectProperty(None, allownone=True)  # None = transparente; '#RRGGBB' = color
    bg_rgba = ListProperty([1, 1, 1, 1])

    has_result  = BooleanProperty(False)
    result_path = StringProperty('')   # resultado a resolución completa
    status_text = StringProperty('')

    _preview_widget_w = 0
    _preview_widget_h = 0

    def on_preview_widget_size(self, w, h):
        """Se llama cuando el widget de preview tiene sus dimensiones reales."""
        if w > 10 and h > 10:
            self._preview_widget_w = w
            self._preview_widget_h = h
            # Si hay imagen cargada y aún no hay copia de trabajo, generarla
            if self.source_path and not self.preview_src_path:
                self._start_preview_copy()

    def tr(self, key):
        return t(key)

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        from kivy.core.window import Window
        Window.clearcolor = (0, 0, 0, 1)
        request_storage_permissions()

        # ─── ESCUCHAMOS EL EVENTO NATIVO ─────────────────────────────────
        if platform == 'android':
            from android import activity
            # Vinculamos el evento on_new_intent a nuestra función
            activity.bind(on_new_intent=self._on_new_intent)
            activity.bind(on_activity_result=self.on_activity_result)

        # Procesamos el intent inicial (por si la app se abrió desde cero compartiendo)
        Clock.schedule_once(lambda dt: self._handle_incoming_intent(), 0.5)

    def _process_intent(self, intent):
        """Lógica unificada para extraer la URI de cualquier Intent."""
        if intent is None:
            return
        try:
            from jnius import autoclass
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
                    # Forzamos de forma segura que la interfaz de Kivy cargue la imagen
                    Clock.schedule_once(lambda dt: self._set_source(local))
        except Exception as e:
            print(f'[Imgridroid] _process_intent error: {e}')

    # ── Intent entrante cuando la app se abre desde CERO ───────────────
    def _handle_incoming_intent(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            intent = PythonActivity.mActivity.getIntent()
            self._process_intent(intent)
        except Exception as e:
            print(f'[Imgridroid] _handle_incoming_intent: {e}')

    # ── Intent entrante cuando la app YA ESTÁ ABIERTA ──────────────────
    def _on_new_intent(self, intent):
        """Este método se gatilla solito gracias a Android cuando mandás algo
        con la app minimizada o abierta en segundo plano.
        """
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            # Buenas prácticas en Android: actualizamos el intent de la activity principal
            PythonActivity.mActivity.setIntent(intent)

            # Procesamos el nuevo archivo entrante
            self._process_intent(intent)
        except Exception as e:
            print(f'[Imgridroid] _on_new_intent error: {e}')

    # ── Selección de imagen ────────────────────────────────────────────
    def open_file_chooser(self):
        """Abre la galería nativa de Android vía ACTION_PICK."""
        if platform == 'android':
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                MediaStore = autoclass('android.provider.MediaStore')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                # ACTION_GET_CONTENT con CATEGORY_OPENABLE abre el selector
                # completo: galería, almacenamiento compartido, apps de archivos, etc.
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType('image/*')
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                String = autoclass('java.lang.String')
                chooser = Intent.createChooser(intent, String(t('choose_image')))
                PythonActivity.mActivity.startActivityForResult(chooser, 1001)
                # El resultado llega via on_activity_result
            except Exception as e:
                self.status_text = str(e)
        else:
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

    def on_activity_result(self, request_code, result_code, intent):
        """Recibe el resultado de startActivityForResult (galería)."""
        RESULT_OK = -1
        if request_code == 1001 and result_code == RESULT_OK and intent:
            try:
                uri = intent.getData()
                if uri:
                    local = resolve_shared_uri_to_path(uri.toString())
                    if local:
                        Clock.schedule_once(lambda dt: self._set_source(local))
            except Exception as e:
                self.status_text = str(e)

    def open_clipboard(self):
        """Lee una imagen del portapapeles y muestra diálogo de confirmación."""
        if platform != 'android':
            self.status_text = t('clipboard_empty')
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            Context = autoclass('android.content.Context')
            ClipboardManager = autoclass('android.content.ClipboardManager')
            clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)

            if not clipboard.hasPrimaryClip():
                self.status_text = t('clipboard_empty')
                return

            clip = clipboard.getPrimaryClip()
            if clip.getItemCount() == 0:
                self.status_text = t('clipboard_empty')
                return

            item = clip.getItemAt(0)
            uri = item.getUri()

            if uri is None:
                self.status_text = t('clipboard_empty')
                return

            local = resolve_shared_uri_to_path(uri.toString())
            if not local:
                self.status_text = t('clipboard_empty')
                return

            self._show_clipboard_preview(local)

        except Exception as e:
            self.status_text = t('clipboard_empty')
            print(f'[Imgridroid] open_clipboard: {e}')

    def _show_clipboard_preview(self, path):
        """Muestra diálogo con miniatura y botones Importar/Descartar."""
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.image import Image as KivyImage
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        layout = BoxLayout(orientation='vertical', spacing='8dp', padding='12dp')
        layout.add_widget(Label(
            text=t('clipboard_preview'),
            size_hint_y=None, height='30dp'
        ))
        layout.add_widget(KivyImage(
            source=path,
            fit_mode='contain',
            size_hint_y=1,
        ))
        btn_row = BoxLayout(size_hint_y=None, height='48dp', spacing='8dp')

        popup = Popup(
            title='',
            content=layout,
            size_hint=(0.9, 0.7),
        )

        def _import(_):
            popup.dismiss()
            self._set_source(path)

        btn_import = Button(text=t('import'))
        btn_import.bind(on_release=_import)
        btn_discard = Button(text=t('discard'))
        btn_discard.bind(on_release=lambda _: popup.dismiss())

        btn_row.add_widget(btn_import)
        btn_row.add_widget(btn_discard)
        layout.add_widget(btn_row)
        popup.open()

    def _set_source(self, path):
        # Verificar tamaño máximo antes de aceptar la imagen
        try:
            from PIL import Image as PILImage
            with PILImage.open(path) as im:
                w, h = im.size
                if w > 4896 or h > 6528:
                    self.status_text = (
                        f'Imagen demasiado grande ({w}×{h}px). '
                        f'Máximo 4896×6528px.'
                    )
                    return
        except Exception as e:
            self.status_text = f'Error al leer imagen: {e}'
            return

        self.source_path = path
        self.result_image = ''   # fuerza el refresco aunque el path sea el mismo
        self.result_image = path
        self._invalidate_result()
        self.status_text = t('preparing')
        self._start_preview_copy()

    def _start_preview_copy(self):
        """Lanza la generación de la copia de trabajo en hilo secundario."""
        if not self.source_path:
            return
        w = self._preview_widget_w
        h = self._preview_widget_h
        # Si el widget aún no tiene dimensiones reales, esperar al on_size
        if w < 10 or h < 10:
            return
        self.preview_src_path = ''
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

    def reset_bg_color(self):
        """Vuelve al fondo transparente (None)."""
        self.bg_hex = None
        self.bg_rgba = [1, 1, 1, 1]
        self._invalidate_result()

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
        bg = self.bg_hex.lstrip('#') if self.bg_hex else 'transparent'
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
                         int(self.gap), self.bg_hex or None)
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
            bg = self.bg_hex.lstrip('#') if self.bg_hex else 'transparent'
            out = join(get_cache_dir(),
                       f'{name}_{self.cols}x{self.rows}_g{self.gap}_{bg}_full.png')
            create_image(self.source_path, out,
                         int(self.cols), int(self.rows),
                         int(self.gap), self.bg_hex or None)
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
