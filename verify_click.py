"""
点击验证器：点一个文字目标，并证明"真的点到了"
=================================================
流程：截图 → OCR 找文字 → 点击 → 再截图 → 比对差异 → 返回 → 确认回到原页面

用法：
    python verify_click.py "功能标记"
    python verify_click.py "设置" --no-back      # 点完不返回

输出会给出：点击坐标、前后画面变化像素数、新页面顶部文字，用来判断是否真的跳转成功。
"""

import argparse
import os
import time

import cv2
import numpy as np

import phone_adb as P


def cap(tag):
    data, err, rc = P.adb(["-s", P.serial(), "exec-out", "screencap", "-p"], binary=True)
    if not data.startswith(b"\x89PNG"):
        raise RuntimeError(f"截图失败：{err}")
    path = os.path.join(P.SHOT_DIR, f"{tag}.png")
    with open(path, "wb") as f:
        f.write(data)
    return path, P.ocr_image(path)


def to_bgr(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--wait", type=float, default=1.8)
    ap.add_argument("--no-back", action="store_true")
    args = ap.parse_args()

    print("[1/4] 截图并识别当前页面")
    p0, d0 = cap("vc_before")
    print(f"     {d0['count']} 行文字")
    cands = P.match_lines(d0, args.text, args.threshold)
    if not cands:
        print(f"     没找到「{args.text}」，当前页面有：")
        for l in d0["lines"][:25]:
            print(f"       [{l['x']},{l['y']}] {l['text']}")
        return 2

    for i, c in enumerate(cands[:5]):
        print(f"     候选#{i} 匹配 {c['score']} 位置 ({c['x']},{c['y']}) {c['text']}")
    if len(cands) > 1 and cands[0]["score"] - cands[1]["score"] < 0.03:
        print("     前两名太接近，请用 --index 指定")
        return 3

    c = cands[args.index]
    x, y = c["x"] + c["w"] // 2, c["y"] + c["h"] // 2
    print(f"[2/4] 点击「{c['text']}」-> ({x},{y})")
    P.s("shell", "input", "tap", str(x), str(y))
    time.sleep(args.wait)

    print("[3/4] 再截图，比对是否真跳转")
    p1, d1 = cap("vc_after")
    a, b = to_bgr(p0), to_bgr(p1)
    if a.shape == b.shape:
        diff = cv2.absdiff(a, b).max(axis=2)
        changed = int((diff > 30).sum())
        ratio = changed / diff.size * 100
        print(f"     变化像素 {changed}（占画面 {ratio:.1f}%）")
    else:
        print(f"     画面尺寸变了 {a.shape} -> {b.shape}（旋转或分屏）")

    title = [l["text"] for l in d1["lines"] if l["y"] < 250]
    print(f"     新页面顶部：{title}")

    if not args.no_back:
        print("[4/4] 返回上一页")
        P.s("shell", "input", "keyevent", "4")
        time.sleep(1.5)
        p2, d2 = cap("vc_back")
        title2 = [l["text"] for l in d2["lines"] if l["y"] < 250]
        print(f"     返回后顶部：{title2}")
        same = abs(d2["count"] - d0["count"]) <= 2
        print(f"     与原页面行数 {d0['count']} vs {d2['count']}：{'一致' if same else '不一致'}")

    print("\n结论：看上面“变化像素”是否明显大于 0、顶部标题是否变了；变了你就是真的点到了。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
