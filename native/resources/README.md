# Native app icon

Graphite tile, teal circuit board, and a silver vault/V mark. The Qt icon is unchanged.
`app.png` is the 1024px transparent master; `app.icns` includes multiple display sizes.

Rebuild with free local tools:

```bash
swift scripts/make_native_icon.swift native/resources/app.png
uv venv build/icon-tools
uv pip install --python build/icon-tools/bin/python Pillow==12.3.0
build/icon-tools/bin/python -c 'from PIL import Image; Image.open("native/resources/app.png").save("native/resources/app.icns")'
```

The native app build consumes the checked-in ICNS; Pillow is only an icon-authoring dependency.
