#!/usr/bin/env python3
from locale import getlocale, LC_ALL, setlocale
from pathlib import Path
from sys import argv, exit
from re import fullmatch, split
from PIL import Image

VERSION = '0.2'

def detect_lang():
    setlocale(LC_ALL, '')
    return (getlocale()[0] or 'en').split('_')[0]

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


def create_image(inp, out, cols, rows, gap, bg):
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
            bg = '#ffffff'
            if Path(out).suffix.lower() == '.png':
                if img.mode == 'RGB':
                    img = img.convert('RGBA')
                bg = (0, 0, 0, 0)

        canvas = Image.new(img.mode, (canvas_width, canvas_height), bg)

        for row in range(rows):
            for col in range(cols):

                pos_x = gap + col * (img.width + gap)
                pos_y = gap + row * (img.height + gap)

                canvas.paste(img, (pos_x, pos_y))

        canvas.save(out)


if __name__ == '__main__':
    try:
        if argv[1] in ['-v', '--version']:
            print(f'{Path(argv[0]).stem} {VERSION}')
            exit(0)
    except IndexError:
        exit(msg(1))

    args = argv[1:]
    if len(args) == 2:
        args.append('')
    if len(args) != 3:
        exit(msg(1))

    pattern_all = (
        r'^[1-9]\d*[Xx×][1-9]\d*'
        r'(?:,\d+)?'
        r'(?:,#(?:[0-9A-Fa-f]{3}){1,2})?$'
    )
    pattern_split = r'[Xx×]'
    aux = {
        'file': {
            'name': [],
            'count': 0,
        },
        'config': {
            'config': '',
            'count': 0
        }
    }
    for a in args:
        if fullmatch(pattern_all, a):
            aux['config']['config'] = a
            aux['config']['count'] += 1
        else:
            aux['file']['name'].append(a)
            aux['file']['count'] += 1

    if aux['file']['count'] != 2 or aux['config']['count'] != 1:
        exit(msg(2))

    list_config = aux['config']['config'].split(',')

    cols, rows = [int(x) for x in split(pattern_split, list_config[0])]

    gap, bg = 0, None

    if len(list_config) == 2:
        if list_config[1].startswith('#'):
            bg = list_config[1]
        else:
            gap = int(list_config[1])

    elif len(list_config) == 3:
        gap, bg = int(list_config[1]), list_config[2]

    inp, out = aux['file']['name']

    f = Path(inp)

    if not f.is_file():
        exit(msg(3))

    if not out:
        out = f'{f.stem}_{cols}x{rows}{f.suffix}'

    try:
        create_image(inp, out, cols, rows, gap, bg)
    except Exception as e:
        print(e)
        exit(msg(4))

    msg(0)
