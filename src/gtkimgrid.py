#!/usr/bin/env python3
"""
gtk-imgrid.py — Interfaz gráfica (GTK4) para create_image().
"""

import gi
gi.require_version('Gtk', '4.0')

from locale import getlocale, LC_ALL, setlocale
from os import environ
from subprocess import DEVNULL, Popen
from platform import system as platform_system
from shutil import copy, rmtree
from sys import argv, exit, modules as sys_modules
from tempfile import mkdtemp, NamedTemporaryFile
from pathlib import Path

from gi.repository import GObject, Gtk, Gdk, Gio, GLib, GdkPixbuf

from PIL import Image
from pyimgrid import create_image

VERSION = '0.1.0'

setlocale(LC_ALL, '')
lang = (getlocale()[0] or 'en').split('_')[0]


def _get_pictures_dir():
    """Devuelve ~/Imágenes, ~/Images, ~/Pictures o ~ según lo que exista."""
    home = Path.home()
    for name in ('Imágenes', 'Images', 'Pictures'):
        candidate = home / name
        if candidate.is_dir():
            return candidate
    return home


def _get_base_path():
    """
    Devuelve la ruta base: _MEIPASS si compilado, parent.parent si script.
    """
    _sys = sys_modules['sys']
    if hasattr(_sys, '_MEIPASS'):
        return Path(_sys._MEIPASS)
    return Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Mensajes de la interfaz
# ---------------------------------------------------------------------------
messages = {
    'es': {
        'title':       'Imagen a cuadrícula',
        'load_image':  'CARGAR IMAGEN',
        'background':  'FONDO',
        'save_image':  'GUARDAR IMAGEN',
        'color_title': 'Elegir color de fondo',
        'open_title':  'Seleccionar imagen',
        'open_types':  'Imágenes',
        'open_all':    'Todos los archivos',
        'save_title':  'Guardar imagen generada',
        'lbl_cols':    'COLUMNAS',
        'lbl_rows':    'FILAS',
        'lbl_gap':     'SEPARADOR',
        'err_no_img':  'Seleccioná una imagen de entrada.',
        'err_int':     "'{}' debe ser un número entero.",
        'err_min':     "'{}' debe ser mayor a {}.",
        'err_min_eq':  "'{}' debe ser mayor o igual a {}.",
        'ok_msg':      'Imagen guardada',
        'open_folder': 'Abrir carpeta',
        'view_image':  'Ver imagen',
        'transparent': 'Transparente',
        'preview_err': 'No se pudo generar la vista previa.',
    },
    'en': {
        'title':       'Image to grid',
        'load_image':  'LOAD IMAGE',
        'background':  'BACKGROUND',
        'save_image':  'SAVE IMAGE',
        'color_title': 'Choose background color',
        'open_title':  'Select image',
        'open_types':  'Images',
        'open_all':    'All files',
        'save_title':  'Save generated image',
        'lbl_cols':    'COLUMNS',
        'lbl_rows':    'ROWS',
        'lbl_gap':     'SEPARATOR',
        'err_no_img':  'Please select an input image.',
        'err_int':     "'{}' must be an integer.",
        'err_min':     "'{}' must be greater than {}.",
        'err_min_eq':  "'{}' must be greater than or equal to {}.",
        'ok_msg':      'Image saved',
        'open_folder': 'Open folder',
        'view_image':  'View image',
        'transparent': 'Transparent',
        'preview_err': 'Could not generate preview.',
    },
}


def tk_msg(key):
    """Devuelve el mensaje en el idioma activo (fallback a inglés)."""
    return messages.get(lang, messages['en']).get(key, key)


VALID_EXTENSIONS = ('.jpeg', '.jpg', '.png')


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class AppWindow(Gtk.ApplicationWindow):

    ERROR_COLOR      = '#c62828'
    PREVIEW_MAX_SIZE = 200    # tamaño máximo (px) de la imagen fuente reducida
    DEBOUNCE_MS      = 300

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title(tk_msg('title'))
        self.set_default_size(520, 460)

        # Ícono de la ventana desde imgrid.svg
        self._set_icon()

        # Estado interno
        self._image_path  = ''
        self._output_path = ''
        self._bg_color    = None    # None = transparente
        self._preview_pixbuf = None

        # Archivo temporal para la imagen fuente reducida (para preview)
        self._preview_src_file = NamedTemporaryFile(
            prefix='gtkimgrid_src_', suffix='.png', delete=False
        )
        self._preview_src_path = self._preview_src_file.name
        self._preview_src_file.close()
        self._preview_src_ready = False

        # Archivo temporal para la imagen de salida de la vista previa
        self._preview_file = NamedTemporaryFile(
            prefix='gtkimgrid_preview_', suffix='.png', delete=False
        )
        self._preview_path = self._preview_file.name
        self._preview_file.close()

        # Id del timeout de debounce para regenerar la vista previa
        self._preview_timeout_id = None

        self.connect('close-request', self._on_close_request)

        self._build_ui()

    # ------------------------------------------------------------------
    # Ícono de la ventana
    # ------------------------------------------------------------------
    def _set_icon(self):
        """Carga imgrid.svg y lo establece como ícono de la ventana."""
        for candidate in (
            _get_base_path() / 'imgrid.svg',
            Path('/usr/share/pixmaps/imgrid.svg'),
        ):
            if not candidate.is_file():
                continue
            try:
                # GTK4 requiere estructura XDG para add_search_path:
                # <dir>/hicolor/scalable/apps/<name>.svg
                # Creamos esa estructura en un directorio temporal.
                icon_dir = Path(mkdtemp(prefix='gtkimgrid_icon_'))
                scalable = icon_dir / 'hicolor' / 'scalable' / 'apps'
                scalable.mkdir(parents=True)
                copy(candidate, scalable / 'imgrid.svg')
                self._icon_tmp_dir = icon_dir   # mantener referencia para limpieza

                icon_theme = Gtk.IconTheme.get_for_display(
                    Gdk.Display.get_default()
                )
                icon_theme.add_search_path(str(icon_dir))
                self.set_icon_name('imgrid')
            except Exception:
                pass
            break

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.set_child(root)

        # ── LOAD IMAGE ──────────────────────────────────────────────
        self._btn_open = Gtk.Button(label=tk_msg('load_image'))
        self._btn_open.connect('clicked', self._on_open_clicked)
        root.append(self._btn_open)

        # Ruta de la imagen seleccionada
        self._lbl_image = Gtk.Label(label='')
        self._lbl_image.set_justify(Gtk.Justification.CENTER)
        self._lbl_image.set_wrap(True)
        root.append(self._lbl_image)

        # Vista previa de la imagen generada (admite arrastrar y soltar)
        self._lbl_preview = Gtk.Picture()
        self._lbl_preview.set_can_shrink(True)
        self._lbl_preview.set_content_fit(Gtk.ContentFit.CONTAIN)
        self._lbl_preview.set_vexpand(True)
        self._lbl_preview.set_size_request(-1, 160)

        preview_frame = Gtk.Frame()
        preview_frame.set_child(self._lbl_preview)

        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)
        drop_target.connect('drop', self._on_drop)
        preview_frame.add_controller(drop_target)

        root.append(preview_frame)

        # ── COLUMNAS / FILAS / SEPARADOR ─────────────────────────────
        box_crg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box_crg.set_homogeneous(True)

        self._spin_cols = self._make_int_field(
            box_crg, tk_msg('lbl_cols'), default=3, min_val=1
        )
        self._spin_rows = self._make_int_field(
            box_crg, tk_msg('lbl_rows'), default=2, min_val=1
        )
        self._spin_gap = self._make_int_field(
            box_crg, tk_msg('lbl_gap'), default=5, min_val=0
        )

        root.append(box_crg)

        # ── BACKGROUND ───────────────────────────────────────────────
        box_bg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._btn_bg = Gtk.Button(label=tk_msg('background'))
        self._btn_bg.set_hexpand(True)
        self._btn_bg.connect('clicked', self._on_pick_color)
        box_bg.append(self._btn_bg)

        # Botón para resetear el fondo a transparente (ícono "edit-clear")
        self._btn_reset_bg = Gtk.Button()
        self._btn_reset_bg.set_icon_name('edit-clear-symbolic')
        self._btn_reset_bg.set_size_request(36, -1)
        self._btn_reset_bg.connect('clicked', self._on_reset_color)
        box_bg.append(self._btn_reset_bg)

        root.append(box_bg)

        # Hex del color elegido o "Transparente" por defecto
        self._lbl_color = Gtk.Label(label=tk_msg('transparent'))
        self._lbl_color.set_justify(Gtk.Justification.CENTER)
        root.append(self._lbl_color)

        # ── SAVE IMAGE ───────────────────────────────────────────────
        self._btn_gen = Gtk.Button(label=tk_msg('save_image'))
        self._btn_gen.connect('clicked', self._on_generate_clicked)
        root.append(self._btn_gen)

        # ── MENSAJE DE ESTADO ────────────────────────────────────────
        box_status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self._lbl_status = Gtk.Label(label='')
        self._lbl_status.set_wrap(True)
        self._lbl_status.set_xalign(0.0)
        self._lbl_status.set_hexpand(True)
        box_status.append(self._lbl_status)

        self._btn_open_folder = Gtk.Button(label=tk_msg('open_folder'))
        self._btn_open_folder.connect('clicked', self._on_open_folder_clicked)
        self._btn_open_folder.set_visible(False)
        box_status.append(self._btn_open_folder)

        self._btn_view_image = Gtk.Button(label=tk_msg('view_image'))
        self._btn_view_image.connect('clicked', self._on_view_image_clicked)
        self._btn_view_image.set_visible(False)
        box_status.append(self._btn_view_image)

        root.append(box_status)

    # ------------------------------------------------------------------
    # Helpers de construcción
    # ------------------------------------------------------------------
    def _make_int_field(self, parent_box, label, default=0, min_val=0):
        """Crea una columna con etiqueta + spinbutton y la agrega al padre."""
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        lbl = Gtk.Label(label=label)
        lbl.set_justify(Gtk.Justification.CENTER)
        frame.append(lbl)

        adjustment = Gtk.Adjustment(
            value=default,
            lower=min_val,
            upper=9999,
            step_increment=1,
            page_increment=10,
        )
        spin = Gtk.SpinButton()
        spin.set_adjustment(adjustment)
        spin.set_value(default)
        spin.set_numeric(True)
        spin.set_halign(Gtk.Align.CENTER)
        spin.connect('value-changed', self._on_spin_changed)
        frame.append(spin)

        parent_box.append(frame)
        return spin

    def _set_status_color(self, label, color, bold=True):
        """Aplica color y negrita al label mediante atributos Pango."""
        weight = 'bold' if bold else 'normal'
        markup = GLib.markup_escape_text(label.get_text())
        label.set_markup(
            f'<span foreground="{color}" font_weight="{weight}">{markup}</span>'
        )

    # ------------------------------------------------------------------
    # Mensajes de estado
    # ------------------------------------------------------------------
    def _show_ok(self, text, with_actions=False):
        """Muestra un mensaje de éxito en negrita."""
        self._lbl_status.set_text(text)
        markup = GLib.markup_escape_text(text)
        self._lbl_status.set_markup(f'<b>{markup}</b>')
        self._btn_open_folder.set_visible(with_actions)
        self._btn_view_image.set_visible(with_actions)

    def _show_error(self, text):
        """Muestra un mensaje de error en rojo y negrita."""
        self._lbl_status.set_text(text)
        self._set_status_color(self._lbl_status, self.ERROR_COLOR)
        self._btn_open_folder.set_visible(False)
        self._btn_view_image.set_visible(False)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _load_image(self, path):
        """Carga path como imagen de entrada y actualiza la UI."""
        self._image_path = path
        self._lbl_image.set_text(path)
        self._btn_open.set_label(Path(path).name)
        self._lbl_status.set_text('')    # limpia estado anterior
        self._btn_open_folder.set_visible(False)
        self._btn_view_image.set_visible(False)
        self._make_preview_source(path)
        self._schedule_preview()

    def _on_drop(self, drop_target, value, x, y):
        """Maneja el drop de un archivo sobre la vista previa."""
        # value puede llegar como URI ("file:///ruta") o como ruta directa
        if not isinstance(value, str):
            return False
        uri = value.strip().splitlines()[0].strip()
        if uri.startswith('file://'):
            path = Gio.File.new_for_uri(uri).get_path()
        else:
            path = uri
        if path and path.lower().endswith(VALID_EXTENSIONS):
            self._load_image(path)
            return True
        return False

    def _on_open_clicked(self, button):
        """Abre el diálogo para seleccionar la imagen de entrada."""
        dialog = Gtk.FileChooserNative.new(
            tk_msg('open_title'),
            self,
            Gtk.FileChooserAction.OPEN,
            None,
            None,
        )
        dialog.set_current_folder(Gio.File.new_for_path(str(_get_pictures_dir())))

        filter_images = Gtk.FileFilter()
        filter_images.set_name(tk_msg('open_types'))
        for ext in ('*.jpeg', '*.jpg', '*.png'):
            filter_images.add_pattern(ext)
        dialog.add_filter(filter_images)

        filter_all = Gtk.FileFilter()
        filter_all.set_name(tk_msg('open_all'))
        filter_all.add_pattern('*')
        dialog.add_filter(filter_all)
        dialog.set_filter(filter_images)

        dialog.connect('response', self._on_open_dialog_response)
        dialog.show()
        self._open_dialog = dialog    # mantener referencia viva

    def _on_open_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                path = file.get_path()
                if path:
                    self._load_image(path)
        dialog.destroy()
        self._open_dialog = None

    def _on_reset_color(self, button):
        """Resetea el fondo a transparente (None)."""
        self._bg_color = None
        self._btn_bg.set_name('')
        self._btn_bg.remove_css_class('bg-color-button')
        ctx = self._btn_bg.get_style_context()
        provider = getattr(self, '_bg_css_provider', None)
        if provider is not None:
            ctx.remove_provider(provider)
            self._bg_css_provider = None
        self._lbl_color.set_text(tk_msg('transparent'))
        self._lbl_color.set_markup(
            GLib.markup_escape_text(tk_msg('transparent'))
        )
        self._schedule_preview()

    def _on_pick_color(self, button):
        """Abre el selector de color para el fondo."""
        dialog = Gtk.ColorChooserDialog(title=tk_msg('color_title'), transient_for=self)
        if self._bg_color:
            rgba = Gdk.RGBA()
            rgba.parse(self._bg_color)
            dialog.set_rgba(rgba)
        dialog.connect('response', self._on_color_dialog_response)
        dialog.show()
        self._color_dialog = dialog    # mantener referencia viva

    def _on_color_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.OK:
            rgba = dialog.get_rgba()
            color = '#{:02x}{:02x}{:02x}'.format(
                round(rgba.red * 255),
                round(rgba.green * 255),
                round(rgba.blue * 255),
            )
            self._bg_color = color

            provider = Gtk.CssProvider()
            css = f'button {{ background-color: {color}; }}'.encode()
            provider.load_from_data(css)
            ctx = self._btn_bg.get_style_context()
            old = getattr(self, '_bg_css_provider', None)
            if old is not None:
                ctx.remove_provider(old)
            ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._bg_css_provider = provider

            self._lbl_color.set_text(color)
            self._set_status_color(self._lbl_color, color, bold=False)
            self._schedule_preview()
        dialog.destroy()
        self._color_dialog = None

    def _on_spin_changed(self, spin):
        self._schedule_preview()

    def _make_preview_source(self, path):
        """Crea una copia reducida de la imagen para usar en la preview."""
        try:
            with Image.open(path) as img:
                copy = img.copy()
                copy.thumbnail(
                    (self.PREVIEW_MAX_SIZE, self.PREVIEW_MAX_SIZE)
                )
                copy.save(self._preview_src_path, format='PNG')
            self._preview_src_ready = True
        except Exception:
            self._preview_src_ready = False

    def _schedule_preview(self):
        """Reinicia el debounce; la preview se regenera tras 300ms quieto."""
        if not self._image_path:
            return
        if self._preview_timeout_id is not None:
            GLib.source_remove(self._preview_timeout_id)
        self._preview_timeout_id = GLib.timeout_add(
            self.DEBOUNCE_MS, self._on_preview_timeout
        )

    def _on_preview_timeout(self):
        self._preview_timeout_id = None
        self._update_preview()
        return GLib.SOURCE_REMOVE

    def _update_preview(self):
        """Genera la imagen de previsualización y la muestra."""
        if not self._image_path:
            return

        cols = self._spin_cols.get_value_as_int()
        rows = self._spin_rows.get_value_as_int()
        gap  = self._spin_gap.get_value_as_int()

        src = (
            self._preview_src_path
            if self._preview_src_ready
            else self._image_path
        )

        try:
            create_image(
                src=src,
                dst=self._preview_path,
                cols=cols,
                rows=rows,
                gap=gap,
                bg=self._bg_color,
            )
            self._preview_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                self._preview_path
            )
            self._apply_preview_pixbuf()
        except Exception:
            self._preview_pixbuf = None
            self._lbl_preview.set_paintable(None)

    def _apply_preview_pixbuf(self):
        """Aplica el pixbuf de la preview al Gtk.Picture."""
        if self._preview_pixbuf is None:
            return
        texture = Gdk.Texture.new_for_pixbuf(self._preview_pixbuf)
        self._lbl_preview.set_paintable(texture)

    def _on_close_request(self, window):
        """Detiene timers y elimina los archivos temporales de vista previa al cerrar."""
        if self._preview_timeout_id is not None:
            GLib.source_remove(self._preview_timeout_id)
            self._preview_timeout_id = None
        for path in (self._preview_path, self._preview_src_path):
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        icon_tmp = getattr(self, '_icon_tmp_dir', None)
        if icon_tmp is not None:
            try:
                rmtree(icon_tmp, ignore_errors=True)
            except Exception:
                pass
        return False    # permitir que la ventana se cierre

    # ------------------------------------------------------------------
    # Abrir carpeta / ver imagen generada
    # ------------------------------------------------------------------
    def _on_open_folder_clicked(self, button):
        """Abre el administrador de archivos con la imagen generada seleccionada."""
        if not self._output_path:
            return
        path = Path(self._output_path)
        system = platform_system()
        try:
            if system == 'Windows':
                Popen(['explorer', '/select,', str(path)])
            elif system == 'Darwin':
                Popen(['open', '-R', str(path)])
            else:
                # Linux: elegir gestor de archivos según el entorno de
                # escritorio activo, con alternativas como respaldo.
                desktop = environ.get('XDG_CURRENT_DESKTOP', '').lower()

                candidates = [
                    ['nautilus', '--select', str(path)],
                    ['dolphin', '--select', str(path)],
                    ['nemo', str(path)],
                    ['thunar', str(path)],
                    ['caja', str(path.parent)],
                    ['pcmanfm-qt', str(path.parent)],
                    ['pcmanfm', str(path.parent)],
                ]

                if 'kde' in desktop or 'plasma' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'dolphin' else 1
                    )
                elif 'gnome' in desktop or 'unity' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'nautilus' else 1
                    )
                elif 'x-cinnamon' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'nemo' else 1
                    )
                elif 'mate' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'caja' else 1
                    )
                elif 'xfce' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'thunar' else 1
                    )
                elif 'lxqt' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'pcmanfm-qt' else 1
                    )
                elif 'lxde' in desktop:
                    candidates.sort(
                        key=lambda c: 0 if c[0] == 'pcmanfm' else 1
                    )

                opened = False
                for cmd in candidates:
                    try:
                        Popen(
                            cmd,
                            stdin=DEVNULL,
                            stdout=DEVNULL,
                            stderr=DEVNULL,
                            start_new_session=True,
                        )
                        opened = True
                        break
                    except FileNotFoundError:
                        continue
                if not opened:
                    Gio.AppInfo.launch_default_for_uri(
                        Gio.File.new_for_path(str(path.parent)).get_uri(),
                        None,
                    )
        except Exception as e:
            self._show_error(str(e))

    def _on_view_image_clicked(self, button):
        """Abre la imagen generada con el visor de imágenes predeterminado."""
        if not self._output_path:
            return
        uri = Gio.File.new_for_path(self._output_path).get_uri()
        Gio.AppInfo.launch_default_for_uri(uri, None)

    # ------------------------------------------------------------------
    # Generar imagen final
    # ------------------------------------------------------------------
    def _on_generate_clicked(self, button):
        """Valida los campos, pide ruta de salida y llama a create_image."""
        # Validar imagen de entrada
        inp = self._image_path.strip()
        if not inp:
            self._show_error(tk_msg('err_no_img'))
            return

        cols = self._spin_cols.get_value_as_int()
        rows = self._spin_rows.get_value_as_int()
        gap  = self._spin_gap.get_value_as_int()

        # Elegir ruta de salida con nombre sugerido
        inp_path  = Path(inp)
        suggested = f'{inp_path.stem}_{cols}x{rows}'

        dialog = Gtk.FileChooserNative.new(
            tk_msg('save_title'),
            self,
            Gtk.FileChooserAction.SAVE,
            None,
            None,
        )
        dialog.set_current_folder(Gio.File.new_for_path(str(inp_path.parent)))
        dialog.set_current_name(suggested + inp_path.suffix)

        # El tipo de la imagen de entrada va primero en la lista
        ext = inp_path.suffix.lower()
        filter_jpeg = Gtk.FileFilter()
        filter_jpeg.set_name('JPEG')
        for pattern in ('*.jpg', '*.jpeg'):
            filter_jpeg.add_pattern(pattern)

        filter_png = Gtk.FileFilter()
        filter_png.set_name('PNG')
        filter_png.add_pattern('*.png')

        filter_all = Gtk.FileFilter()
        filter_all.set_name(tk_msg('open_all'))
        filter_all.add_pattern('*')

        if ext in ('.jpg', '.jpeg'):
            order = (filter_jpeg, filter_png, filter_all)
        else:
            order = (filter_png, filter_jpeg, filter_all)

        for f in order:
            dialog.add_filter(f)
        dialog.set_filter(order[0])

        self._gen_params = (inp, inp_path, cols, rows, gap)
        dialog.connect('response', self._on_save_dialog_response)
        dialog.show()
        self._save_dialog = dialog    # mantener referencia viva

    def _on_save_dialog_response(self, dialog, response):
        if response != Gtk.ResponseType.ACCEPT:
            dialog.destroy()
            self._save_dialog = None
            return

        file = dialog.get_file()
        dialog.destroy()
        self._save_dialog = None

        if not file:
            return

        out = file.get_path()
        if not out:
            return

        inp, inp_path, cols, rows, gap = self._gen_params

        # Si el usuario no especificó extensión, usar la de origen
        if not Path(out).suffix:
            out = out + inp_path.suffix

        # Generar la imagen
        try:
            create_image(
                src=inp,
                dst=out,
                cols=cols,
                rows=rows,
                gap=gap,
                bg=self._bg_color,
            )
            self._output_path = out
            self._show_ok(tk_msg('ok_msg'), with_actions=True)
        except Exception as e:
            self._show_error(str(e))


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
class App(Gtk.Application):

    def __init__(self):
        super().__init__(
            application_id='org.imgrid.gtkimgrid',
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )
        self._window = None

    def do_activate(self):
        if self._window is None:
            self._window = AppWindow(self)
        self._window.present()

    def do_open(self, files, n_files, hint):
        self.do_activate()
        if n_files >= 1:
            path = files[0].get_path()
            if path and path.lower().endswith(('.jpeg', '.jpg', '.png')):
                self._window._load_image(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':

    try:
        if argv[1] in ('-v', '--version'):
            print(f'{Path(argv[0]).stem} {VERSION}')
            exit(0)
    except IndexError:
        pass

    app = App()
    exit(app.run(argv))
