import html, os, re, subprocess, sys

WIKI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(WIKI, "_site")

PAGES = [
    ("README.md", "首页与编写规范"),
    ("00-前言.md", "前言"),
    ("01-规划业务场景.md", "一、规划业务场景"),
    ("02-组织资源管理.md", "二、组织资源管理"),
    ("03-接入与管理资源.md", "三、接入与管理资源"),
    ("04-项目与资源申请.md", "四、项目与资源申请"),
    ("05-构建知识库.md", "五、构建知识库"),
    ("06-构建本体.md", "六、构建本体"),
    ("07-通用能力.md", "七、通用能力"),
    ("08-建设Agent.md", "八、建设 Agent"),
    ("09-对外开放.md", "九、对外开放"),
    ("10-门户检索问答.md", "十、门户检索问答"),
    ("11-日常维护与运营.md", "十一、日常维护与运营"),
    ("12-附录A术语.md", "附录 A 术语与入口"),
    ("13-附录B-Logic节点.md", "附录 B Logic 节点"),
    ("CHANGELOG.md", "v3.4 → v4.0 变更清单"),
    ("待确认汇总.md", "待确认汇总"),
]

CSS = """
*{box-sizing:border-box}body{margin:0;font:15px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#1f2329;background:#f5f6f8}
nav{position:fixed;top:0;left:0;bottom:0;width:250px;overflow:auto;background:#fff;border-right:1px solid #e5e6eb;padding:18px 0}
nav h1{font-size:15px;margin:0 18px 12px;color:#1456f0}
nav a{display:block;padding:6px 18px;color:#1f2329;text-decoration:none;font-size:14px}
nav a:hover{background:#f2f3f5}nav a.on{background:#e8f0ff;color:#1456f0;font-weight:600}
main{margin-left:250px;display:flex;gap:24px;padding:24px 32px}
article{flex:1;min-width:0;max-width:980px;background:#fff;border-radius:8px;padding:28px 40px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
aside{width:220px;position:sticky;top:24px;align-self:flex-start;max-height:calc(100vh - 48px);overflow:auto;font-size:13px}
aside ul{list-style:none;padding-left:10px;margin:0}aside>ul{padding-left:0}aside a{color:#646a73;text-decoration:none;display:block;padding:2px 0}aside a:hover{color:#1456f0}
h1{font-size:26px;border-bottom:1px solid #e5e6eb;padding-bottom:10px}h2{font-size:21px;margin-top:36px}h3{font-size:17px;margin-top:28px}
img{max-width:100%;border:1px solid #e5e6eb;border-radius:4px;margin:8px 0;cursor:zoom-in}
table{border-collapse:collapse;margin:12px 0;font-size:14px}th,td{border:1px solid #dee0e3;padding:6px 10px;vertical-align:top}th{background:#f5f6f8}
code{background:#f2f3f5;padding:1px 5px;border-radius:3px;font-size:13px}blockquote{margin:12px 0;padding:8px 14px;border-left:3px solid #1456f0;background:#f5f8ff;color:#4e5969}
#zoom{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:9;align-items:center;justify-content:center;cursor:zoom-out}#zoom img{max-width:95vw;max-height:95vh;border:0}
"""

JS = """
document.querySelectorAll('article img').forEach(i=>i.onclick=()=>{const z=document.getElementById('zoom');z.querySelector('img').src=i.src;z.style.display='flex'});
document.getElementById('zoom').onclick=e=>e.currentTarget.style.display='none';
"""


def convert(md):
    src = open(os.path.join(WIKI, md), encoding="utf-8").read()
    src = re.sub(r"(\]\()(?!https?:|#)([^)]+?)\.md(#[^)]*)?\)", lambda m: f"{m.group(1)}{m.group(2)}.html{m.group(3) or ''})", src)
    src = re.sub(r"(\]\(|<img src=\")(?=images/|_ref/)", r"\1../", src)
    body = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "html", "--toc", "--toc-depth=3", "--template", os.path.join(OUT, ".tpl")],
        input=src, capture_output=True, text=True, check=True,
    ).stdout
    toc, _, content = body.partition("\x00SPLIT\x00")
    return toc, content


def main():
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, ".tpl"), "w").write("$toc$\x00SPLIT\x00$body$")
    for md, title in PAGES:
        name = "index.html" if md == "README.md" else md[:-3] + ".html"
        nav = "".join(
            f'<a href="{"index.html" if m == "README.md" else m[:-3] + ".html"}"{" class=on" if m == md else ""}>{html.escape(t)}</a>'
            for m, t in PAGES
        )
        toc, content = convert(md)
        page = (
            f'<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>{html.escape(title)} - 产品使用手册 v4.0</title>'
            f"<style>{CSS}</style></head><body><nav><h1>赛豆产品使用手册 v4.0</h1>{nav}</nav>"
            f"<main><article>{content}</article><aside>{toc}</aside></main>"
            f'<div id="zoom"><img alt=""></div><script>{JS}</script></body></html>'
        )
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(page)
    os.remove(os.path.join(OUT, ".tpl"))
    print("built", len(PAGES), "pages ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
