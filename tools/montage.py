#!/usr/bin/env python3
"""montage.py OUT.png IN.png...: tile screenshots two per row at half size, for quick review."""
import sys
from PIL import Image
ims = [Image.open(f).convert('RGB') for f in sys.argv[2:]]
w, h = ims[0].size
rows = (len(ims) + 1) // 2
m = Image.new('RGB', (w * 2, h * rows))
for i, im in enumerate(ims):
    m.paste(im, ((i % 2) * w, (i // 2) * h))
m.resize((w, h * rows // 2)).save(sys.argv[1])
