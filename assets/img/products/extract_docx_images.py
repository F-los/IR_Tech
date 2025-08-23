#!/usr/bin/env python3
import zipfile, shutil, os, sys, tempfile, subprocess
from pathlib import Path

# 1) 제품 루트 자동 탐지: asset/ 또는 assets/
CANDIDATES = [Path("asset/img/products"), Path("assets/img/products")]
roots = [p.resolve() for p in CANDIDATES if p.exists()]
if not roots:
    print("제품 폴더를 찾지 못했습니다: asset/img/products 또는 assets/img/products 가 존재해야 합니다.")
    sys.exit(1)
print("검색 루트:", ", ".join(str(r) for r in roots))

def has_cmd(name):
    from shutil import which
    return which(name) is not None

HAS_MAGICK = has_cmd("magick") or has_cmd("convert")  # ImageMagick

def convert_emf_wmf(src: Path, dst_png: Path):
    # ImageMagick이 있으면 EMF/WMF -> PNG 변환
    cmd = ["magick" if has_cmd("magick") else "convert", str(src), str(dst_png)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False

total_docx = 0
total_copied = 0
summary = []

for root in roots:
    for docx_path in root.rglob("*.docx"):
        total_docx += 1
        product_dir = docx_path.parent
        out_dir = product_dir / "images"
        out_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        converted = 0

        with tempfile.TemporaryDirectory() as tmpd:
            try:
                with zipfile.ZipFile(docx_path) as z:
                    names = [n for n in z.namelist() if n.startswith("word/media/")]
                    if not names:
                        summary.append((docx_path, 0, 0))
                        continue
                    for n in names:
                        fn = Path(n).name
                        with z.open(n) as src:
                            tmp_file = Path(tmpd) / fn
                            with open(tmp_file, "wb") as f:
                                f.write(src.read())

                        # 대상 파일명: 문서이름__원본파일명
                        # 예: hijet_e_line_en__image1.png
                        base = f"{docx_path.stem}__{fn}"
                        dst = out_dir / base

                        ext = tmp_file.suffix.lower()
                        if ext in [".emf", ".wmf"] and HAS_MAGICK:
                            dst_png = dst.with_suffix(".png")
                            if convert_emf_wmf(tmp_file, dst_png):
                                converted += 1
                                copied += 1
                                continue
                            # 변환 실패 시 원본 그대로 복사
                        shutil.copy2(tmp_file, dst)
                        copied += 1

                summary.append((docx_path, copied, converted))
                total_copied += copied
            except zipfile.BadZipFile:
                # 손상되었거나 docx가 아닌 파일
                summary.append((docx_path, 0, 0))

print(f"처리한 DOCX: {total_docx}개, 추출한 이미지: {total_copied}개")
if not HAS_MAGICK:
    print("참고: ImageMagick이 없어 EMF/WMF 변환은 건너뜀")

# 간단 출력
for docx_path, copied, converted in summary[:50]:
    print(f"- {docx_path}: {copied}개 추출 (EMF/WMF→PNG 변환 {converted}개)")
