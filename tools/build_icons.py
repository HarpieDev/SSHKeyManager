"""Exporte le logo SVG en PNG et en ICO Windows à plusieurs résolutions."""
import os
import struct
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ui.components import _PATHS


def render_png(renderer, size):
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(data)


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication([])
    directory = ROOT / "assets" / "icons"
    renderer = QSvgRenderer(str(directory / "harpie.svg"))
    assert renderer.isValid()
    sizes = (16, 20, 24, 32, 40, 48, 64, 128, 256)
    images = [render_png(renderer, size) for size in sizes]
    offset = 6 + 16 * len(sizes)
    entries = []
    for size, data in zip(sizes, images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (directory / "harpie.ico").write_bytes(struct.pack("<HHH", 0, 1, len(sizes)) + b"".join(entries) + b"".join(images))
    (directory / "harpie.png").write_bytes(render_png(renderer, 512))
    for name, path in _PATHS.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" color="#B6B2C4" stroke="#B6B2C4" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
        (directory / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"Logo SVG, PNG, ICO ({len(sizes)} tailles) et {len(_PATHS)} icônes générés.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
