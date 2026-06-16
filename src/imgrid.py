#!/usr/bin/env python3
from locale import getlocale, LC_ALL, setlocale
from pathlib import Path
from sys import argv, exit
from re import fullmatch, split

from pyimgrid import create_image

VERSION = '0.0.3'

setlocale(LC_ALL, '')
lang = (getlocale()[0] or 'en').split('_')[0]

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

    default_name = f'{f.stem}_{cols}x{rows}{f.suffix}'

    if not out:
        out = default_name
    elif Path(out).is_dir():
        out = str(Path(out) / default_name)

    try:
        create_image(inp, out, cols, rows, gap, bg)
    except Exception as e:
        print(e)
        exit(msg(4))

    msg(0)
