"""Bundle index.html + style.css + app.js into one self-contained HTML file.

Usage:  python build_single.py [output.html] [--fragment]
  --fragment  emit only the page body (title, style, markup, script) for hosts
              that wrap the page in their own <html>/<head> skeleton.
"""
import pathlib
import re
import sys

here = pathlib.Path(__file__).parent
html = (here / "index.html").read_text(encoding="utf-8")
css = (here / "style.css").read_text(encoding="utf-8")
js = (here / "app.js").read_text(encoding="utf-8")

body = html.split("<!--APP-->", 1)[1].split("<!--/APP-->", 1)[0]
title = re.search(r"<title>(.*?)</title>", html).group(1)
fonts = re.search(r'<link rel="stylesheet" href="(https://fonts[^"]+)">', html).group(1)
js_safe = js.replace("</script", "<\\/script")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = pathlib.Path(args[0]) if args else here / "darkroom-single.html"

if "--fragment" in sys.argv:
    doc = (f"<title>{title}</title>\n"
           f'<link rel="stylesheet" href="{fonts}">\n'
           f"<style>\n{css}</style>\n{body}<script>\n{js_safe}</script>\n")
else:
    head = html.split("<!--APP-->", 1)[0]
    head = re.sub(r'<link rel="(manifest|icon|apple-touch-icon)"[^>]*>\n?', "", head)
    head = head.replace('<link rel="stylesheet" href="style.css">', f"<style>\n{css}</style>")
    doc = f"{head}{body}<script>\n{js_safe}</script>\n</body>\n</html>\n"

out.write_text(doc, encoding="utf-8")
print(f"wrote {out} ({len(doc) // 1024} KB)")
