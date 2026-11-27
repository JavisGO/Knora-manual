import glob, os, re, shutil, subprocess, sys, zipfile

from PIL import Image

WIKI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANUAL_DIR = os.path.dirname(WIKI)
TMP = "/tmp/wordbuild2"
TEMPLATE = os.path.join(MANUAL_DIR, "赛豆企业知识平台产品使用手册（v3.4）.docx")
OUT = os.path.join(MANUAL_DIR, "赛豆企业知识平台产品使用手册（v4.0）.docx")


def read(p):
    return open(p, encoding="utf-8").read()


def regen_summaries():
    files = sorted(glob.glob(os.path.join(WIKI, "[0-9][0-9]-*.md")))
    demote = lambda s: re.sub(r"^(#{2,4}) ", lambda x: "#" * (len(x.group(1)) + 1) + " ", s.strip(), flags=re.M)
    nimg = len(os.listdir(os.path.join(WIKI, "images")))
    chg = ["# v3.4 → v4.0 变更清单\n", "> 全书用词：原「空间」统一改称「部门」（界面原文「个人空间」「默认企业空间」保留）。\n",
           f"> 由各章末尾「本章变更说明」汇总；详细说明以各章为准。截图：`images/` 共 {nimg} 张（`-proto` 为 1130 版本原型示意）。\n"]
    tbc = ["# 待确认事项汇总\n", "> 由各章末尾「待确认」汇总，供产品/研发/用户逐条确认；确认后回到对应章节修改正文并删除该条。\n"]
    total = 0
    for f in files:
        t = read(f)
        name = os.path.basename(f)
        title = t.split("\n", 1)[0].lstrip("# ").strip()
        m = re.search(r"^## 本章变更说明.*?\n(.*?)(?=^## 待确认)", t, re.S | re.M)
        m2 = re.search(r"^## 待确认.*?\n(.*)$", t, re.S | re.M)
        if m:
            chg.append(f"\n## {title}（[{name}]({name})）\n\n" + demote(m.group(1)).strip("-").strip() + "\n")
        if m2:
            body = m2.group(1).strip()
            n = len(re.findall(r"^\s*\d+\.\s", body, re.M))
            total += n
            tbc.append(f"\n## {title}（[{name}]({name})，{n} 条）\n\n" + demote(body) + "\n")
    tbc.insert(2, f"\n共约 {total} 条。\n")
    open(os.path.join(WIKI, "CHANGELOG.md"), "w", encoding="utf-8").write("\n".join(chg))
    open(os.path.join(WIKI, "待确认汇总.md"), "w", encoding="utf-8").write("\n".join(tbc))
    return total


def merge_body():
    parts = []
    for f in sorted(glob.glob(os.path.join(WIKI, "[0-9][0-9]-*.md"))):
        t = read(f)
        t = re.split(r"^---\s*\n(?=\s*## 本章变更说明)|^## 本章变更说明", t, flags=re.M)[0].rstrip().rstrip("-").rstrip()
        t = re.sub(r"^> 本(文件|片段).*\n\n?", "", t, flags=re.M)
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        parts.append(t)
    return "\n\n".join(parts)


def compress_images(body):
    rs = os.path.join(TMP, "rs")
    shutil.rmtree(rs, ignore_errors=True)
    os.makedirs(os.path.join(rs, "images"))
    os.makedirs(os.path.join(rs, "_ref/v3.4-media/media"))

    def conv(src, dst):
        im = Image.open(src)
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        if im.mode in ("RGBA", "P", "LA"):
            im = im.convert("RGB")
        im.save(dst, quality=85, optimize=True)

    for f in glob.glob(os.path.join(WIKI, "images", "*.png")):
        conv(f, os.path.join(rs, "images", os.path.basename(f)[:-4] + ".jpg"))
    conv(os.path.join(WIKI, "_ref/v3.4-media/media/image1.png"), os.path.join(rs, "_ref/v3.4-media/media/image1.jpg"))
    body = re.sub(r"(images/[^)\s\"]+|_ref/v3\.4-media/media/image1)\.png", r"\1.jpg", body)
    open(os.path.join(rs, "manual.md"), "w", encoding="utf-8").write(body)
    return rs


def light_reference():
    d = os.path.join(TMP, "refx")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(d)
    shutil.rmtree(os.path.join(d, "word/media"), ignore_errors=True)
    p = os.path.join(d, "word/_rels/document.xml.rels")
    t = read(p)
    t = re.sub(r'<Relationship [^>]*Type="[^"]*/image"[^>]*/>', "", t)
    open(p, "w", encoding="utf-8").write(t)
    p = os.path.join(d, "word/document.xml")
    t = read(p)
    sect = re.findall(r"<w:sectPr.*?</w:sectPr>", t, re.S)[-1]
    t = t[: t.index("<w:body>") + 8] + "<w:p/>" + sect + "</w:body></w:document>"
    open(p, "w", encoding="utf-8").write(t)
    out = os.path.join(TMP, "ref-light.docx")
    if os.path.exists(out):
        os.remove(out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for root, _, names in os.walk(d):
            for n in names:
                full = os.path.join(root, n)
                zo.write(full, os.path.relpath(full, d))
    return out


def post_process(src, dst):
    border = "<w:tblBorders>" + "".join(
        f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        for s in ["top", "left", "bottom", "right", "insideH", "insideV"]) + "</w:tblBorders>"
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename == "word/styles.xml":
                s = data.decode()
                s = s.replace('<w:tblPr><w:tblCellMar><w:top w:type="dxa" w:w="0" />',
                              "<w:tblPr>" + border + '<w:tblCellMar><w:top w:type="dxa" w:w="40" />', 1)
                s = s.replace('<w:tblStylePr w:type="firstRow"><w:tblPr /><w:tcPr><w:tcBorders><w:bottom w:color="auto" w:space="0" w:sz="0" w:val="single" /></w:tcBorders><w:vAlign w:val="bottom" /></w:tcPr>',
                              '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/></w:rPr><w:tblPr /><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="F2F3F5"/><w:vAlign w:val="bottom" /></w:tcPr>', 1)
                data = s.encode()
            if it.filename == "word/settings.xml":
                s = data.decode()
                if "updateFields" not in s:
                    s = re.sub(r"(<w:settings[^>]*>)", r'\1<w:updateFields w:val="true"/>', s, count=1)
                data = s.encode()
            if it.filename == "word/document.xml":
                d = data.decode()

                def fix(m):
                    p = m.group(0)
                    if "<w:drawing>" in p or re.search(r"<w:t[^>]*>图 \d+-\d+", p):
                        if "<w:jc " not in p:
                            p = (p.replace("<w:pPr>", '<w:pPr><w:jc w:val="center"/>', 1) if "<w:pPr>" in p
                                 else p.replace("<w:r>", '<w:pPr><w:jc w:val="center"/></w:pPr><w:r>', 1))
                    return p

                d = re.sub(r"<w:p>.*?</w:p>|<w:p [^>]*>.*?</w:p>", fix, d, flags=re.S)
                data = d.encode()
            zo.writestr(it, data)


def main():
    os.makedirs(TMP, exist_ok=True)
    total = regen_summaries()
    rs = compress_images(merge_body())
    ref = light_reference()
    raw = os.path.join(TMP, "raw.docx")
    subprocess.run(["pandoc", "manual.md", "-f", "gfm+pipe_tables", "-t", "docx", "--resource-path=.", "--toc", "--toc-depth=3",
                    "-M", "toc-title=目录", "-M", "title=赛豆企业知识平台产品使用手册（v4.0）",
                    "-M", "subtitle=依据测试环境编写", f"--reference-doc={ref}", "-o", raw], cwd=rs, check=True)
    post_process(raw, OUT)
    print("待确认", total, "条;", OUT, round(os.path.getsize(OUT) / 1e6, 1), "MB")


if __name__ == "__main__":
    sys.exit(main())
