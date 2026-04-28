#!/usr/bin/env python3
"""Bundle filler.html + dependencies into a single offline claim-form.html.

Reads from this directory:
  filler.html              — template (the Mac dev version)
  claim-form-part-b.pdf    — blank form
  field-map.json           — calibrated field positions
  defaults.json (optional) — saved hospital defaults (Export button in filler)
  pdf-lib.min.js (cached)  — auto-downloaded once from unpkg

Writes:
  claim-form.html          — single self-contained file for offline use

Usage:
  python3 bundle.py
"""
import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
PDF_LIB_URL = 'https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js'
PDF_LIB_CACHE = ROOT / 'pdf-lib.min.js'
PDF_LIB_SCRIPT_TAG = '<script src="https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.min.js"></script>'


def fetch_pdf_lib() -> str:
    if PDF_LIB_CACHE.exists():
        print(f'  using cached {PDF_LIB_CACHE.name}')
        return PDF_LIB_CACHE.read_text()
    print(f'  downloading {PDF_LIB_URL} ...')
    code = urllib.request.urlopen(PDF_LIB_URL, timeout=30).read().decode()
    PDF_LIB_CACHE.write_text(code)
    print(f'  cached as {PDF_LIB_CACHE.name}')
    return code


def main() -> int:
    template_path = ROOT / 'filler.html'
    pdf_path = ROOT / 'claim-form-part-b.pdf'
    map_path = ROOT / 'field-map.json'

    for p in (template_path, pdf_path, map_path):
        if not p.exists():
            print(f'ERROR: required file missing: {p}', file=sys.stderr)
            return 1

    print('Reading sources...')
    template = template_path.read_text()
    pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode()
    field_map = json.loads(map_path.read_text())

    defaults_path = ROOT / 'defaults.json'
    if defaults_path.exists():
        defaults = json.loads(defaults_path.read_text())
        print(f'  loaded {len(defaults)} hospital defaults from defaults.json')
    else:
        defaults = {}
        print('  no defaults.json found — bundle ships with empty defaults.')
        print('  (run the filler in your browser, click "Export" next to "Save these",')
        print('   place defaults.json here, and re-run bundle.py.)')

    print('Inlining pdf-lib...')
    pdf_lib = fetch_pdf_lib()

    if PDF_LIB_SCRIPT_TAG not in template:
        print(f'ERROR: could not find pdf-lib script tag in filler.html', file=sys.stderr)
        return 2
    template = template.replace(
        PDF_LIB_SCRIPT_TAG,
        f'<script>/* pdf-lib v1.17.1 inlined */\n{pdf_lib}\n</script>'
    )

    inline_block = (
        '<script>\n'
        f'window.__INLINE_FIELD_MAP__ = {json.dumps(field_map)};\n'
        f'window.__INLINE_DEFAULTS__ = {json.dumps(defaults)};\n'
        f'window.__INLINE_PDF_BASE64__ = "{pdf_b64}";\n'
        '(function () {\n'
        '  var orig = window.fetch;\n'
        '  window.fetch = function (url) {\n'
        '    if (typeof url === "string") {\n'
        '      if (url.indexOf("field-map.json") !== -1) {\n'
        '        return Promise.resolve({ json: function () { return Promise.resolve(window.__INLINE_FIELD_MAP__); } });\n'
        '      }\n'
        '      if (url.indexOf("claim-form-part-b.pdf") !== -1) {\n'
        '        var bin = atob(window.__INLINE_PDF_BASE64__);\n'
        '        var buf = new Uint8Array(bin.length);\n'
        '        for (var i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);\n'
        '        return Promise.resolve({ arrayBuffer: function () { return Promise.resolve(buf.buffer); } });\n'
        '      }\n'
        '    }\n'
        '    return orig.apply(this, arguments);\n'
        '  };\n'
        '})();\n'
        '</script>\n'
    )

    if '<body>' not in template:
        print('ERROR: could not find <body> tag in filler.html', file=sys.stderr)
        return 3
    template = template.replace('<body>', '<body>\n' + inline_block, 1)

    template = template.replace(
        '<title>Claim Form Filler</title>',
        '<title>Hospital Claim Form</title>'
    )

    output_path = ROOT / 'claim-form.html'
    output_path.write_text(template)
    size_kb = output_path.stat().st_size // 1024
    print(f'\nDone. Wrote {output_path.name} ({size_kb} KB).')
    print('Email or USB this single file to your father — works offline in any modern browser.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
