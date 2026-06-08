# ImGrid

A command-line tool that splits an image into a grid of tiles. Includes an optional GUI built with Tkinter.

![ImGrid screenshot](screenshots/imgrid.gif)

---

## Requirements

- [Pillow](https://python-pillow.org/)
- [CairoSVG](https://cairosvg.org/)

```bash
pip install pillow cairosvg
```

## Usage

```
./imgrid INPUT GRID [OUTPUT]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `INPUT`  | Yes | Path to the source image |
| `GRID`   | Yes | Grid dimensions in `COLUMNSxROWS` format |
| `OUTPUT` | No | Path for the output image (auto-generated if omitted) |

### Grid format

The grid is specified as `COLUMNSxROWS`. The separator can be any of:
- `x` (lowercase)
- `X` (uppercase)
- `×` (multiplication sign)

## Examples

```bash
# Split into 2 columns × 3 rows, save to output.jpg
./imgrid input.jpg 2x3 output.jpg

# Using uppercase X
./imgrid photo.png 4X2 result.png

# Using the multiplication sign
./imgrid image.jpg 3×3

# Omitting output (auto-generated filename)
./imgrid input.jpg 2x3
```

## GUI

A graphical interface is available via Tkinter. Run it with:

```bash
./tkimgrid
```

> **Debian users:** Tkinter is not bundled with Python and must be installed separately:
> ```bash
> sudo apt install python3-tkinter
> ```

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

---

![Captura de pantalla de ImGrid](screenshots/imgrid.gif)

Herramienta de línea de comandos que divide una imagen en una cuadrícula de fragmentos. Incluye una interfaz gráfica opcional con Tkinter.

## Requisitos

- [Pillow](https://python-pillow.org/)
- [CairoSVG](https://cairosvg.org/)

```bash
pip install pillow cairosvg
```

## Uso

```
./imgrid ENTRADA CUADRÍCULA [SALIDA]
```

### Argumentos

| Argumento     | Requerido | Descripción |
|---------------|-----------|-------------|
| `ENTRADA`     | Sí | Ruta a la imagen original |
| `CUADRÍCULA`  | Sí | Dimensiones de la cuadrícula en formato `COLUMNASxFILAS` |
| `SALIDA`      | No | Ruta para la imagen de salida (se genera automáticamente si se omite) |

### Formato de cuadrícula

La cuadrícula se especifica como `COLUMNASxFILAS`. El separador puede ser cualquiera de:
- `x` (minúscula)
- `X` (mayúscula)
- `×` (signo de multiplicación)

## Ejemplos

```bash
# Dividir en 2 columnas × 3 filas, guardar en output.jpg
./imgrid input.jpg 2x3 output.jpg

# Usando X mayúscula
./imgrid foto.png 4X2 resultado.png

# Usando el signo de multiplicación
./imgrid imagen.jpg 3×3

# Sin especificar salida (nombre generado automáticamente)
./imgrid input.jpg 2x3
```

## Interfaz gráfica

Está disponible una interfaz gráfica mediante Tkinter. Para ejecutarla:

```bash
./tkimgrid
```

> **Usuarios de Debian:** Tkinter no viene incluido con Python y debe instalarse por separado:
> ```bash
> sudo apt install python3-tkinter
> ```

## Licencia

Este proyecto está licenciado bajo la [Licencia Pública General de GNU v3.0](LICENSE).
