#!/usr/bin/env python3
import os, sys, math
from pathlib import Path
from PIL import Image, ImageStat
import numpy as np

ROOT_CANDIDATES = [Path("asset/img/products"), Path("assets/img/products")]

def find_root():
    for p in ROOT_CANDIDATES:
        if p.exists():
            return p.resolve()
    print("asset/img/products 또는 assets/img/products 폴더가 필요합니다.")
    sys.exit(1)

def image_score(p: Path):
    try:
        im = Image.open(p)
        w, h = im.size
        area = w * h

        # 알파(투명) 비율
        alpha_ratio = 0.0
        if im.mode in ("RGBA", "LA"):
            alpha = np.array(im.split()[-1], dtype=np.uint8)
            alpha_ratio = (alpha < 10).mean()  # 거의 투명 픽셀 비율

        # 색 다양성(저해상도 로고는 색이 적다)
        small = im.convert("RGB").resize((min(256, w), min(256, h)))
        arr = np.array(small)
        uniques = len(np.unique(arr.reshape(-1, 3), axis=0))

        # 흑백 선화 여부(표준편차가 아주 낮고 색이 적음)
        gray = small.convert("L")
        stat = ImageStat.Stat(gray)
        std = math.sqrt(stat.var[0])

        # 매우 흰색/검정 비율(선화·배경)
        g = np.array(gray)
        white_ratio = (g > 245).mean()
        black_ratio = (g < 10).mean()

        # 파일 확장자 가중치(JPEG 우선)
        ext_bonus = 0.0
        if p.suffix.lower() in [".jpg", ".jpeg", ".webp"]:
            ext_bonus = 0.5

        # 점수 구성
        # 기본: 면적 로그스케일
        s = math.log1p(area) / 15.0
        s += ext_bonus
        # 색 다양성 보너스
        s += min(uniques / 400.0, 0.8)
        # 대비/질감 보너스
        s += min(std / 40.0, 0.8)
        # 패널티: 투명 배경(로고), 과도한 흰/검정, 너무 작은 것
        s -= alpha_ratio * 1.0
        s -= max(0.0, white_ratio - 0.6) * 1.2
        s -= max(0.0, black_ratio - 0.6) * 0.8
        if area < 250_000:  # 500x500 미만 정도는 강한 패널티
            s -= 2.0
        return s, (w, h), uniques, std, alpha_ratio, white_ratio, black_ratio
    except Exception:
        return -1e9, (0,0), 0, 0.0, 0.0, 0.0, 0.0

def choose_and_write(folder: Path):
    imgs = []
    for ext in ("*.png","*.jpg","*.jpeg","*.webp","*.bmp"):
        imgs += list(folder.glob(ext))
    if not imgs:
        return None

    scored = []
    for p in imgs:
        s, wh, u, std, ar, wr, br = image_score(p)
        scored.append((s, p, wh, u, std, ar, wr, br))
    scored.sort(reverse=True, key=lambda x: x[0])

    best = scored[0]
    best_path = best[1]

    # 출력 위치
    out_main = folder / "product.jpg"
    out_thumb = folder / "thumb.jpg"

    # 저장(최대 1600px로 리사이즈)
    im = Image.open(best_path).convert("RGB")
    w, h = im.size
    maxw = 1600
    if w > maxw:
        nh = int(h * (maxw / w))
        im = im.resize((maxw, nh), Image.LANCZOS)
    im.save(out_main, quality=92)

    # 썸네일(가로 1200px)
    th = Image.open(best_path).convert("RGB")
    tw, thh = th.size
    tmax = 1200
    if tw > tmax:
        th = th.resize((tmax, int(thh * (tmax/tw))), Image.LANCZOS)
    th.save(out_thumb, quality=88)

    return best_path.name

def main():
    root = find_root()
    targets = []
    # images 폴더가 있는 모든 제품 경로 순회
    for images_dir in root.rglob("images"):
        targets.append(images_dir)

    if not targets:
        print("images 폴더를 찾지 못했습니다. 먼저 DOCX 추출을 완료하세요.")
        return

    print(f"대상 images 폴더: {len(targets)}개")
    done = 0
    for d in targets:
        picked = choose_and_write(d)
        if picked:
            done += 1
            print(f"[OK] {d} -> {picked} 선택, product.jpg / thumb.jpg 생성")
        else:
            print(f"[SKIP] {d} 에서 후보 없음")
    print(f"완료: {done}개 폴더 처리")

if __name__ == "__main__":
    main()
