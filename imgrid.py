#!/usr/bin/env python3
from locale import getlocale, LC_ALL, setlocale
from pathlib import Path
from sys import argv, exit
from re import match, split
from PIL import Image

def detect_lang():
    setlocale(LC_ALL, '')
    return (getlocale()[0] or 'en').split('_')

lang = detect_lang()

def msg(n:int):
    m = {
        'es': [
            'Imagen guardada correctamente.',
            'Cantidad de argumentos incorrecta.',
            'Argumentos inválidos.',
            'Archivo de entrada inexistente.',
            'Error al generar la imagen.'
        ],
        'en': [
            'Image saved successfully.',
            'Wrong number of arguments.',
            'Invalid arguments.',
            'Input file not found.',
            'Failed to generate image.'
        ]
    }
    print(m.get(lang, m['en'])[n])
    return n


def create_image(inp, out, cols, rows, gap=5, bg=None):
    with Image.open(inp) as img:

        canvas_width = (
            img.width * cols
            + gap * (cols + 1)
        )

        canvas_height = (
            img.height * rows
            + gap * (rows + 1)
        )

        if bg is None:
            bg = (255, 255, 255, 255) if img.mode == 'RGBA' else 'white'

        canvas = Image.new(img.mode, (canvas_width, canvas_height), bg)

        for row in range(rows):
            for col in range(cols):

                pos_x = gap + col * (img.width + gap)
                pos_y = gap + row * (img.height + gap)

                canvas.paste(img, (pos_x, pos_y))

        canvas.save(out)


if __name__ == '__main__':
    args = argv[1:]
    if len(args) == 2:
        args.append('')
    if len(args) != 3:
        exit(msg(1))

    pattern_grid = r'^[1-9]\d*[Xx×][1-9]\d*$'
    pattern_split = r'[Xx×]'
    aux = {
        'file': {
            'name': [],
            'count': 0,
        },
        'grid': {
            'grid': '',
            'count': 0
        }
    }
    for a in args:
        if match(pattern_grid, a):
            aux['grid']['grid'] = a
            aux['grid']['count'] += 1
        else:
            aux['file']['name'].append(a)
            aux['file']['count'] += 1

    if aux['file']['count'] != 2 or aux['grid']['count'] != 1:
        exit(msg(2))

    cols, rows = [int(x) for x in split(pattern_split, aux['grid']['grid'])]

    inp, out = aux['file']['name']

    f = Path(inp)

    if not f.is_file():
        exit(msg(3))

    if not out:
        out = f'{f.stem}_{cols}x{rows}{f.suffix}'

    try:
        create_image(inp, out, cols, rows)
    except Exception as e:
        print(e)
        exit(msg(4))

    msg(0)
