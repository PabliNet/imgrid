#!/usr/bin/env python3
"""
qtimgrid.py — Interfaz gráfica (Qt) para create_image().
"""

from locale import getlocale, LC_ALL, setlocale
from os import environ
from platform import system as platform_system
from sys import argv, exit, modules as sys_modules
from subprocess import DEVNULL, Popen
from tempfile import NamedTemporaryFile
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import (
    QDesktopServices, QIcon, QImage, QKeySequence, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from PIL import Image
from pyimgrid import create_image

VERSION = '0.2.0'


def _get_windows_lang():
    """Devuelve el código de idioma corto (ej: 'es', 'en') en Windows."""
    import ctypes
    windll = ctypes.windll.kernel32
    lcid = windll.GetUserDefaultUILanguage()
    # Buffer para el nombre del locale (ej: "es-AR", "en-US")
    buf = ctypes.create_unicode_buffer(85)
    windll.LCIDToLocaleName(lcid, buf, 85, 0)
    if buf.value:
        return buf.value.split('-')[0]  # "es-AR" -> "es"
    return 'en'


def _detect_lang():
    """Detecta el idioma del sistema (con rama específica para Windows)."""
    if platform_system() == 'Windows':
        try:
            return _get_windows_lang()
        except Exception:
            return 'en'
    setlocale(LC_ALL, '')
    return (getlocale()[0] or 'en').split('_')[0]


lang = _detect_lang()


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
        'copy_image':  'COPIAR',
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
        'copy_ok':     'Imagen copiada al portapapeles',
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
        'copy_image':  'COPY',
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
        'copy_ok':     'Image copied to clipboard',
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


class _PreviewLabel(QLabel):
    """QLabel que acepta arrastrar y soltar archivos de imagen."""

    def __init__(self, on_drop, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_drop = on_drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            path = url.toLocalFile()
            if path.lower().endswith(VALID_EXTENSIONS):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(VALID_EXTENSIONS):
                self._on_drop(path)
                event.acceptProposedAction()
                return
        event.ignore()


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class App(QMainWindow):

    OK_COLOR  = '#888888'
    ERROR_COLOR   = '#c62828'
    PREVIEW_MAX_SIZE = 200    # tamaño máximo (px) de la imagen fuente reducida

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tk_msg('title'))
        self.setMinimumSize(520, 460)
        self.resize(520, 460)

        # Ícono de la ventana desde imgrid.svg
        self._set_icon()

        # Estado interno
        self._image_path = ''
        self._output_path = ''
        self._bg_color   = None    # None = transparente
        self._preview_pixmap = None

        # Archivo temporal para la imagen fuente reducida (para preview)
        self._preview_src_file = NamedTemporaryFile(
            prefix='qtimgrid_src_', suffix='.png', delete=False
        )
        self._preview_src_path = self._preview_src_file.name
        self._preview_src_file.close()
        self._preview_src_ready = False

        # Archivo temporal para la imagen de salida de la vista previa
        self._preview_file = NamedTemporaryFile(
            prefix='qtimgrid_preview_', suffix='.png', delete=False
        )
        self._preview_path = self._preview_file.name
        self._preview_file.close()

        # Timer de debounce para regenerar la vista previa
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._update_preview)

        # Archivo temporal donde se vuelca la imagen pegada del portapapeles
        self._clipboard_file = NamedTemporaryFile(
            prefix='qtimgrid_clip_', suffix='.png', delete=False
        )
        self._clipboard_img_path = self._clipboard_file.name
        self._clipboard_file.close()

        # Archivo temporal para la imagen generada a copiar al portapapeles
        self._copy_file = NamedTemporaryFile(
            prefix='qtimgrid_copy_', suffix='.png', delete=False
        )
        self._copy_out_path = self._copy_file.name
        self._copy_file.close()

        self._build_ui()

        # Pegar con el atajo estándar del sistema (Ctrl+V / Cmd+V)
        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.activated.connect(self._paste_from_clipboard)

    # ------------------------------------------------------------------
    # Ícono de la ventana
    # ------------------------------------------------------------------
    def _set_icon(self):
        """Carga imgrid.svg y lo establece como ícono de la ventana."""
        svg_path = _get_base_path() / 'imgrid.svg'
        if not svg_path.is_file():
            svg_path = Path('/usr/share/pixmaps/imgrid.svg')
        if svg_path.is_file():
            self.setWindowIcon(QIcon(str(svg_path)))

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── LOAD IMAGE ──────────────────────────────────────────────
        self._btn_open = QPushButton(tk_msg('load_image'))
        self._btn_open.clicked.connect(self._open_image)
        layout.addWidget(self._btn_open)

        # Ruta de la imagen seleccionada
        self._lbl_image = QLabel('')
        self._lbl_image.setAlignment(Qt.AlignCenter)
        self._lbl_image.setWordWrap(True)
        layout.addWidget(self._lbl_image)

        # Vista previa de la imagen generada (admite arrastrar y soltar)
        self._lbl_preview = _PreviewLabel(self._load_image)
        self._lbl_preview.setText('')
        self._lbl_preview.setAlignment(Qt.AlignCenter)
        self._lbl_preview.setMinimumHeight(160)
        self._lbl_preview.setFrameShape(QFrame.StyledPanel)
        layout.addWidget(self._lbl_preview, stretch=1)

        # ── COLUMNAS / FILAS / SEPARADOR ─────────────────────────────
        frame_crg = QHBoxLayout()

        self._spin_cols = self._make_int_field(
            frame_crg, tk_msg('lbl_cols'), default=3, min_val=1
        )
        self._spin_rows = self._make_int_field(
            frame_crg, tk_msg('lbl_rows'), default=2, min_val=1
        )
        self._spin_gap  = self._make_int_field(
            frame_crg, tk_msg('lbl_gap'),  default=5, min_val=0
        )

        layout.addLayout(frame_crg)

        # ── BACKGROUND ───────────────────────────────────────────────
        frame_bg = QHBoxLayout()

        self._btn_bg = QPushButton(tk_msg('background'))
        self._btn_bg.clicked.connect(self._pick_color)
        frame_bg.addWidget(self._btn_bg, stretch=1)

        # Botón para resetear el fondo a transparente (ícono "edit-clear")
        self._btn_reset_bg = QPushButton()
        reset_icon = QIcon.fromTheme('edit-clear')
        if not reset_icon.isNull():
            self._btn_reset_bg.setIcon(reset_icon)
        else:
            self._btn_reset_bg.setText('×')
        self._btn_reset_bg.setFixedWidth(36)
        self._btn_reset_bg.clicked.connect(self._reset_color)
        frame_bg.addWidget(self._btn_reset_bg)

        layout.addLayout(frame_bg)

        # Hex del color elegido o "Transparente" por defecto
        self._lbl_color = QLabel(tk_msg('transparent'))
        self._lbl_color.setAlignment(Qt.AlignCenter)
        self._set_status_color(self._lbl_color, self.OK_COLOR, bold=False)
        layout.addWidget(self._lbl_color)

        # ── SAVE IMAGE / COPIAR ──────────────────────────────────────
        frame_gen = QHBoxLayout()

        self._btn_gen = QPushButton(tk_msg('save_image'))
        self._btn_gen.clicked.connect(self._generate)
        frame_gen.addWidget(self._btn_gen, stretch=1)

        self._btn_copy = QPushButton(tk_msg('copy_image'))
        self._btn_copy.clicked.connect(self._copy_to_clipboard)
        frame_gen.addWidget(self._btn_copy, stretch=1)

        layout.addLayout(frame_gen)

        # ── MENSAJE DE ESTADO ────────────────────────────────────────
        frame_status = QHBoxLayout()

        self._lbl_status = QLabel('')
        self._lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_status.setWordWrap(True)
        frame_status.addWidget(self._lbl_status, stretch=1)

        self._btn_open_folder = QPushButton(tk_msg('open_folder'))
        self._btn_open_folder.clicked.connect(self._open_output_folder)
        self._btn_open_folder.setVisible(False)
        frame_status.addWidget(self._btn_open_folder)

        self._btn_view_image = QPushButton(tk_msg('view_image'))
        self._btn_view_image.clicked.connect(self._view_output_image)
        self._btn_view_image.setVisible(False)
        frame_status.addWidget(self._btn_view_image)

        layout.addLayout(frame_status)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Helpers de construcción
    # ------------------------------------------------------------------
    def _make_int_field(self, parent_layout, label, default=0, min_val=0):
        """Crea un sub-layout con etiqueta + spinbox y lo agrega al padre."""
        frame = QVBoxLayout()

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        frame.addWidget(lbl)

        spin = QSpinBox()
        spin.setMinimum(min_val)
        spin.setMaximum(9999)
        spin.setValue(default)
        spin.setAlignment(Qt.AlignCenter)
        spin.valueChanged.connect(self._schedule_preview)
        frame.addWidget(spin)

        parent_layout.addLayout(frame)
        return spin

    @staticmethod
    def _set_status_color(label, color, bold=True):
        """Aplica color y negrita al label sin afectar el resto del tema."""
        weight = 'bold' if bold else 'normal'
        label.setStyleSheet(f'color: {color}; font-weight: {weight};')

    # ------------------------------------------------------------------
    # Mensajes de estado
    # ------------------------------------------------------------------
    def _show_ok(self, text, with_actions=False):
        """Muestra un mensaje de éxito en negrita con el color del tema."""
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet('font-weight: bold;')
        self._btn_open_folder.setVisible(with_actions)
        self._btn_view_image.setVisible(with_actions)

    def _show_error(self, text):
        """Muestra un mensaje de error en rojo y negrita."""
        self._lbl_status.setText(text)
        self._set_status_color(self._lbl_status, self.ERROR_COLOR)
        self._btn_open_folder.setVisible(False)
        self._btn_view_image.setVisible(False)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _load_image(self, path):
        """Carga path como imagen de entrada y actualiza la UI."""
        self._image_path = path
        self._lbl_image.setText(path)
        self._btn_open.setText(Path(path).name)
        self._lbl_status.setText('')    # limpia estado anterior
        self._btn_open_folder.setVisible(False)
        self._btn_view_image.setVisible(False)
        self._make_preview_source(path)
        self._schedule_preview()

    def _paste_from_clipboard(self):
        """Toma la imagen del portapapeles (si hay) y la carga como entrada."""
        image = QApplication.clipboard().image()
        if image.isNull():
            return
        try:
            image.save(self._clipboard_img_path, 'PNG')
            self._load_image(self._clipboard_img_path)
        except Exception as e:
            self._show_error(str(e))

    def _open_image(self):
        """Abre el diálogo para seleccionar la imagen de entrada."""
        types = (
            f"{tk_msg('open_types')} (*.jpeg *.jpg *.png);;"
            f"{tk_msg('open_all')} (*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            tk_msg('open_title'),
            str(_get_pictures_dir()),
            types,
        )
        if path:
            self._load_image(path)

    def _reset_color(self):
        """Resetea el fondo a transparente (None)."""
        self._bg_color = None
        self._btn_bg.setStyleSheet('')
        self._lbl_color.setText(tk_msg('transparent'))
        self._set_status_color(self._lbl_color, self.OK_COLOR, bold=False)
        self._schedule_preview()

    def _pick_color(self):
        """Abre el selector de color para el fondo."""
        initial = self._bg_color or '#ffffff'
        color = QColorDialog.getColor(
            initial, self, tk_msg('color_title')
        )
        if color.isValid():
            self._bg_color = color.name()
            self._btn_bg.setStyleSheet(
                f'background-color: {self._bg_color};'
            )
            self._lbl_color.setText(self._bg_color)
            self._set_status_color(self._lbl_color, self._bg_color, bold=False)
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
        if self._image_path:
            self._preview_timer.start()

    def _update_preview(self):
        """Genera la imagen de previsualización y la muestra escalada."""
        if not self._image_path:
            return

        cols = self._spin_cols.value()
        rows = self._spin_rows.value()
        gap  = self._spin_gap.value()

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
            self._preview_pixmap = QPixmap(self._preview_path)
            self._apply_preview_pixmap()
        except Exception:
            self._preview_pixmap = None
            self._lbl_preview.setText(tk_msg('preview_err'))

    def _apply_preview_pixmap(self):
        """Escala el pixmap de la preview al tamaño actual del label."""
        if not getattr(self, '_preview_pixmap', None):
            return
        scaled = self._preview_pixmap.scaled(
            self._lbl_preview.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._lbl_preview.setPixmap(scaled)

    def resizeEvent(self, event):
        """Re-escala la preview cuando la ventana cambia de tamaño."""
        super().resizeEvent(event)
        self._apply_preview_pixmap()

    def closeEvent(self, event):
        """Detiene timers y elimina los archivos temporales de vista previa al cerrar."""
        self._preview_timer.stop()
        for path in (self._preview_path, self._preview_src_path,
                     self._clipboard_img_path, self._copy_out_path):
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        super().closeEvent(event)

    def _open_output_folder(self):
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
                    QDesktopServices.openUrl(
                        QUrl.fromLocalFile(str(path.parent))
                    )
        except Exception as e:
            self._show_error(str(e))

    def _view_output_image(self):
        """Abre la imagen generada con el visor de imágenes predeterminado."""
        if not self._output_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._output_path))

    def _copy_to_clipboard(self):
        """Genera la imagen final y la copia al portapapeles."""
        inp = self._image_path.strip()
        if not inp:
            self._show_error(tk_msg('err_no_img'))
            return

        cols = self._spin_cols.value()
        rows = self._spin_rows.value()
        gap  = self._spin_gap.value()

        try:
            create_image(
                src=inp,
                dst=self._copy_out_path,
                cols=cols,
                rows=rows,
                gap=gap,
                bg=self._bg_color,
            )
            image = QImage(self._copy_out_path)
            QApplication.clipboard().setImage(image)
            self._show_ok(tk_msg('copy_ok'))
        except Exception as e:
            self._show_error(str(e))

    def _generate(self):
        """Valida los campos, pide ruta de salida y llama a create_image."""
        # Validar imagen de entrada
        inp = self._image_path.strip()
        if not inp:
            self._show_error(tk_msg('err_no_img'))
            return

        cols = self._spin_cols.value()
        rows = self._spin_rows.value()
        gap  = self._spin_gap.value()

        # Elegir ruta de salida con nombre sugerido
        inp_path  = Path(inp)
        suggested = f'{inp_path.stem}_{cols}x{rows}'

        # El tipo de la imagen de entrada va primero en la lista
        ext = inp_path.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            types = "JPEG (*.jpg *.jpeg);;PNG (*.png);;" + \
                    f"{tk_msg('open_all')} (*)"
        else:
            types = "PNG (*.png);;JPEG (*.jpg *.jpeg);;" + \
                    f"{tk_msg('open_all')} (*)"

        out, _ = QFileDialog.getSaveFileName(
            self,
            tk_msg('save_title'),
            str(Path(inp_path.parent) / suggested),
            types,
        )
        if not out:
            return    # usuario canceló

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
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':

    try:
        if argv[1] in ('-v', '--version'):
            print(f'{Path(argv[0]).stem} {VERSION}')
            exit(0)
    except IndexError:
        pass

    # Leer el argumento antes de QApplication, que puede modificar argv
    initial_image = None
    try:
        candidate = argv[1]
        if candidate.lower().endswith(('.jpeg', '.jpg', '.png')):
            initial_image = candidate
    except IndexError:
        pass

    # Silenciar warnings ruidosos al generar miniaturas en QFileDialog
    environ['QT_LOGGING_RULES'] = 'qt.gui.imageio.jpeg=false'

    qt_app = QApplication(argv)
    window = App()

    if initial_image:
        window._load_image(initial_image)

    window.show()
    exit(qt_app.exec())
