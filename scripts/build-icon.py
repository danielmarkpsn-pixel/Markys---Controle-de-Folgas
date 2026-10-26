"""Gera o ícone Windows MARKYS em vários tamanhos com Pillow, sem dependências nativas."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "markys.ico"

def draw_icon(size: int) -> Image.Image:
    scale = size / 256
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def xy(values): return tuple(round(v * scale) for v in values)
    d.rounded_rectangle(xy((5, 5, 251, 251)), radius=round(37*scale), fill=(39, 78, 115, 255), outline=(124, 177, 215, 255), width=max(1, round(4*scale)))
    # Calendário dourado.
    d.rounded_rectangle(xy((70, 35, 186, 123)), radius=round(12*scale), fill=(124, 177, 215, 255))
    d.rounded_rectangle(xy((82, 56, 174, 112)), radius=round(5*scale), fill=(39, 78, 115, 255))
    for x in (94, 119, 144):
        for y in (68, 89): d.rounded_rectangle(xy((x, y, x+12, y+10)), radius=max(1, round(2*scale)), fill=(220, 237, 250, 255))
    for x in (91, 158): d.rounded_rectangle(xy((x, 25, x+10, 52)), radius=round(5*scale), fill=(220, 237, 250, 255))
    # M prateado e arco dourado, mantendo leitura em tamanhos pequenos.
    d.polygon([xy((36, 91)), xy((66, 91)), xy((128, 147)), xy((190, 91)), xy((220, 91)), xy((220, 177)), xy((194, 177)), xy((194, 133)), xy((128, 190)), xy((62, 133)), xy((62, 177)), xy((36, 177))], fill=(242, 248, 253, 255))
    d.arc(xy((35, 100, 224, 218)), start=15, end=165, fill=(124, 177, 215, 255), width=max(2, round(13*scale)))
    return im

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base = draw_icon(256)
    base.save(OUT, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Ícone MARKYS criado: {OUT}")

if __name__ == "__main__": main()
