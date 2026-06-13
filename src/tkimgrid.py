"""
image_tool.py — Interfaz gráfica para create_image().
"""

from io import BytesIO
from sys import argv, exit
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog

from cairosvg import svg2png
from PIL import Image, ImageTk
from imgrid import create_image, lang, VERSION


def _get_pictures_dir():
    """Devuelve ~/Imágenes, ~/Images, ~/Pictures o ~ según lo que exista."""
    home = Path.home()
    for name in ('Imágenes', 'Images', 'Pictures'):
        candidate = home / name
        if candidate.is_dir():
            return candidate
    return home


def _get_base_path():
    """Devuelve la ruta base: _MEIPASS si compilado, parent.parent si script."""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
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
        'ok_msg':      'Imagen guardada en: {}',
        'transparent': 'Transparente',
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
        'ok_msg':      'Image saved at: {}',
        'transparent': 'Transparent',
    },
}


def tk_msg(key):
    """Devuelve el mensaje en el idioma activo (fallback a inglés)."""
    return messages.get(lang, messages['en']).get(key, key)


# ---------------------------------------------------------------------------
# Validación de enteros
# ---------------------------------------------------------------------------
def _validate_int(value, name, minimum):
    """Convierte value a int y verifica que sea >= minimum."""
    try:
        n = int(value)
    except ValueError:
        raise ValueError(tk_msg('err_int').format(name))
    if n < minimum:
        if minimum == 0:
            raise ValueError(tk_msg('err_min_eq').format(name, minimum))
        raise ValueError(tk_msg('err_min').format(name, minimum - 1))
    return n


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class App(tk.Tk):

    PAD         = 12
    BTN_WIDTH   = 60
    ENTRY_WIDTH = 6
    BG          = '#000000'
    WIDGET_BG   = '#1a1a1a'
    FG          = '#e0e0e0'
    ACCENT      = '#4a9eff'
    BORDER      = '#444444'
    ERR_COLOR   = '#ff4444'
    OK_COLOR    = '#888888'
    OK_GEN      = '#ffff00'
    DEFAULT_BG  = None
    FONT        = ('sans serif', 14)
    FONT_BTN    = ('', 14, 'bold')
    FONT_MSG    = ('', 14)

    def __init__(self):
        super().__init__()
        self.title(tk_msg('title'))
        self.resizable(False, False)
        self.configure(bg=self.BG)

        # Ícono de la ventana desde logo.svg
        self._set_icon()

        # Estado interno
        self._image_path = tk.StringVar(value='')
        self._bg_color   = self.DEFAULT_BG    # color predeterminado

        self._build_ui()

    # ------------------------------------------------------------------
    # Ícono de la ventana
    # ------------------------------------------------------------------
    def _set_icon(self):
        """Carga logo.svg y lo establece como ícono de la ventana."""
        svg_path = _get_base_path() / 'imgrid.svg'
        try:
            png_data = svg2png(
                url=str(svg_path), output_width=64, output_height=64
            )
            img = Image.open(BytesIO(png_data))
            self._icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._icon)
        except Exception as e:
            pass    # si falla, la ventana usa el ícono por defecto

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def _build_ui(self):
        p = self.PAD

        # ── LOAD IMAGE ──────────────────────────────────────────────
        self._btn_open = self._make_button(
            self, tk_msg('load_image'), self._open_image
        )
        self._btn_open.pack(fill='x', padx=p, pady=(p, 0))

        # Ruta de la imagen seleccionada
        self._lbl_image = tk.Label(
            self,
            textvariable=self._image_path,
            bg=self.BG,
            fg='#ffffff',
            font=('Courier', 14),
            wraplength=600,
            justify='center',
        )
        self._lbl_image.pack(padx=p, pady=(2, 0), anchor='center')

        # ── COLUMNAS / FILAS / SEPARADOR ─────────────────────────────
        frame_crg = tk.Frame(self, bg=self.BG)
        frame_crg.pack(padx=p, pady=(p, 0), fill='x')

        self._entry_cols = self._make_int_field(
            frame_crg, tk_msg('lbl_cols'), default=3, min_val=1
        )
        self._entry_rows = self._make_int_field(
            frame_crg, tk_msg('lbl_rows'), default=2, min_val=1
        )
        self._entry_gap  = self._make_int_field(
            frame_crg, tk_msg('lbl_gap'),  default=5, min_val=0
        )

        for widget in frame_crg.winfo_children():
            widget.pack(side='left', expand=True)

        # ── BACKGROUND ───────────────────────────────────────────────
        frame_bg = tk.Frame(self, bg=self.BG)
        frame_bg.pack(padx=p, pady=(p, 0), fill='x')

        self._btn_bg = self._make_button(
            frame_bg, tk_msg('background'), self._pick_color
        )
        self._btn_bg.pack(side='left', fill='x', expand=True)

        # Botón × para resetear el fondo a transparente
        self._btn_reset_bg = tk.Button(
            frame_bg,
            text='×',
            command=self._reset_color,
            font=self.FONT_BTN,
            bg=self.WIDGET_BG,
            fg=self.ACCENT,
            activebackground=self.BORDER,
            activeforeground=self.FG,
            relief='groove',
            bd=1,
            cursor='hand2',
            padx=10,
            pady=6,
        )
        self._btn_reset_bg.pack(side='left', padx=(4, 0))

        # Hex del color elegido o "Transparente" por defecto
        self._lbl_color = tk.Label(
            self,
            text=tk_msg('transparent'),
            bg=self.BG,
            fg=self.OK_COLOR,
            font=self.FONT_MSG,
        )
        self._lbl_color.pack(pady=(2, 0))

        # ── SAVE IMAGE ───────────────────────────────────────────────
        self._btn_gen = self._make_button(
            self, tk_msg('save_image'), self._generate
        )
        self._btn_gen.pack(fill='x', padx=p, pady=(p, 0))

        # ── MENSAJE DE ESTADO ────────────────────────────────────────
        # Crece según el largo del path; wraplength acota el ancho
        self._lbl_status = tk.Label(
            self,
            text='',
            bg=self.BG,
            fg=self.OK_COLOR,
            font=self.FONT_MSG,
            wraplength=600,
            justify='left',
        )
        self._lbl_status.pack(padx=p, pady=(4, p), anchor='w', fill='x')

    # ------------------------------------------------------------------
    # Helpers de construcción
    # ------------------------------------------------------------------
    def _make_button(self, parent, text, command):
        """Crea y devuelve un botón con el estilo de la app."""
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=self.FONT_BTN,
            bg=self.WIDGET_BG,
            fg=self.ACCENT,
            activebackground=self.BORDER,
            activeforeground=self.FG,
            relief='groove',
            bd=1,
            cursor='hand2',
            width=self.BTN_WIDTH,
            pady=6,
        )

    def _make_int_field(self, parent, label, default=0, min_val=0):
        """Crea un frame con etiqueta + entry; las flechas cambian el valor."""
        frame = tk.Frame(parent, bg=self.BG)

        tk.Label(
            frame,
            text=label,
            bg=self.BG,
            fg=self.FG,
            font=self.FONT,
        ).pack()

        entry = tk.Entry(
            frame,
            width=self.ENTRY_WIDTH,
            font=self.FONT,
            bg=self.WIDGET_BG,
            fg=self.FG,
            insertbackground=self.FG,
            relief='groove',
            bd=1,
            justify='center',
        )
        entry.insert(0, str(default))    # valor predeterminado
        entry.pack()

        # Flecha arriba +1, flecha abajo -1 (respetando min_val)
        entry.bind('<Up>',   lambda e: self._step(entry, +1, min_val))
        entry.bind('<Down>', lambda e: self._step(entry, -1, min_val))

        return entry

    @staticmethod
    def _step(entry, delta, min_val=0):
        """Incrementa o decrementa el valor del entry respetando min_val."""
        try:
            value = int(entry.get())
        except ValueError:
            value = min_val
        new_value = max(min_val, value + delta)
        entry.delete(0, tk.END)
        entry.insert(0, str(new_value))

    # ------------------------------------------------------------------
    # Mensajes de estado (reemplazan messagebox)
    # ------------------------------------------------------------------
    def _show_ok(self, text):
        """Muestra un mensaje de éxito en amarillo."""
        self._lbl_status.configure(text=text, fg=self.OK_GEN)

    def _show_error(self, text):
        """Muestra un mensaje de error en rojo."""
        self._lbl_status.configure(text=text, fg=self.ERR_COLOR)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _open_image(self):
        """Abre el diálogo para seleccionar la imagen de entrada."""
        path = filedialog.askopenfilename(
            title=tk_msg('open_title'),
            initialdir=_get_pictures_dir(),
            filetypes=[
                (tk_msg('open_types'), '*.jpeg *.jpg *.png'),
                (tk_msg('open_all'),   '*.*'),
            ],
        )
        if path:
            self._image_path.set(path)
            self._btn_open.configure(text=Path(path).name)
            self._lbl_status.configure(text='')    # limpia estado anterior

    def _reset_color(self):
        """Resetea el fondo a transparente (None)."""
        self._bg_color = None
        self._btn_bg.configure(bg=self.WIDGET_BG)
        self._lbl_color.configure(
            text=tk_msg('transparent'),
            fg=self.OK_COLOR,
        )

    def _pick_color(self):
        """Abre el selector de color para el fondo."""
        color = colorchooser.askcolor(
            title=tk_msg('color_title'),
            color=self._bg_color or '#ffffff',
        )
        # askcolor devuelve ((r, g, b), '#rrggbb') o (None, None)
        if color and color[1]:
            self._bg_color = color[1]
            self._btn_bg.configure(bg=self._bg_color)
            self._lbl_color.configure(
                text=self._bg_color,
                fg=self._bg_color,
            )

    def _generate(self):
        """Valida los campos, pide ruta de salida y llama a create_image."""
        # Validar imagen de entrada
        inp = self._image_path.get().strip()
        if not inp:
            self._show_error(tk_msg('err_no_img'))
            return

        # Validar COLUMNAS, FILAS y SEPARADOR
        try:
            cols = _validate_int(
                self._entry_cols.get(), tk_msg('lbl_cols'), 1
            )
            rows = _validate_int(
                self._entry_rows.get(), tk_msg('lbl_rows'), 1
            )
            gap  = _validate_int(
                self._entry_gap.get() or '0', tk_msg('lbl_gap'), 0
            )
        except ValueError as e:
            self._show_error(str(e))
            return

        # Elegir ruta de salida con nombre sugerido
        inp_path  = Path(inp)
        suggested = f'{inp_path.stem}_{cols}x{rows}'

        # El tipo de la imagen de entrada va primero en la lista
        ext = inp_path.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            filetypes = [
                ('JPEG', '*.jpg *.jpeg'),
                ('PNG',  '*.png'),
                (tk_msg('open_all'), '*.*'),
            ]
        else:
            filetypes = [
                ('PNG',  '*.png'),
                ('JPEG', '*.jpg *.jpeg'),
                (tk_msg('open_all'), '*.*'),
            ]

        out = filedialog.asksaveasfilename(
            title=tk_msg('save_title'),
            initialfile=suggested,
            defaultextension=inp_path.suffix,
            filetypes=filetypes,
        )
        if not out:
            return    # usuario canceló

        # Generar la imagen
        try:
            create_image(
                inp=inp,
                out=out,
                cols=cols,
                rows=rows,
                gap=gap,
                bg=self._bg_color,
            )
            self._show_ok(tk_msg('ok_msg').format(out))
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

    app = App()
    app.mainloop()
