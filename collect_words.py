"""
词卡采集器：自动翻词卡并记录单词/音标/词义
==========================================
每一页读取"大标题单词 + 音标 + 词义"，点右下角「继续」翻页，直到重复或找不到按钮。

用法：
    python collect_words.py --steps 20
    python collect_words.py --steps 50 --out words/unit.md

产出：
    words/words.jsonl   逐条追加，程序中断也不丢
    words/<时间>.md     人类可读的词表
"""

import argparse
import json
import os
import re
import time

import phone_adb as P

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "words")


def cap(tag="tmp"):
    data, err, rc = P.adb(["-s", P.serial(), "exec-out", "screencap", "-p"], binary=True)
    if not data.startswith(b"\x89PNG"):
        raise RuntimeError(f"截图失败：{err}")
    path = os.path.join(P.SHOT_DIR, f"{tag}.png")
    with open(path, "wb") as f:
        f.write(data)
    return path, P.ocr_image(path)


def parse_card(d):
    """
    从一页 OCR 结果里取三样东西：
      单词   —— y 在 400~620 之间、字号最大的那行
      音标   —— y 在 620~720，含 [ ] 的行
      词义   —— y 在 860~1000 的行（可能被拆成两三段，拼起来）
    """
    lines = d.get("lines", [])
    word, phonetic, meaning = "", "", []

    cands = [l for l in lines if 400 <= l["y"] <= 620]
    if cands:
        cands.sort(key=lambda l: (-l["h"], l["y"]))
        word = cands[0]["text"].strip()

    for l in lines:
        if 600 <= l["y"] <= 730 and ("[" in l["text"] or "]" in l["text"]):
            phonetic = l["text"].strip()
            break

    for l in lines:
        if 860 <= l["y"] <= 1010:
            t = l["text"].strip()
            if t and "查看" not in t:
                meaning.append(t)

    # 词义被拆成「noun 部门，」+「行业，领域」这种，按 x 排序拼接
    if len(meaning) > 1:
        seq = sorted([l for l in lines if 860 <= l["y"] <= 1010], key=lambda l: l["x"])
        meaning = [s["text"].strip() for s in seq if s["text"].strip()]
    return word, phonetic, " ".join(meaning).replace("  ", " ").strip()


def find_continue(d):
    for l in d.get("lines", []):
        if re.sub(r"\s+", "", l["text"]) in ("继续", "下一步", "完成"):
            return l
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--wait", type=float, default=1.2)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    jsonl = os.path.join(OUT_DIR, "words.jsonl")
    md_path = args.out or os.path.join(OUT_DIR, time.strftime("%m%d_%H%M") + ".md")

    seen = {}
    if os.path.exists(jsonl):
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                    seen[o["word"]] = o
                except Exception:
                    pass
        print(f"已有记录 {len(seen)} 个词，本次继续累积")

    rows = []
    last_word = None
    for i in range(args.steps):
        path, d = cap(f"card_{i:02d}")
        word, phonetic, meaning = parse_card(d)
        if not word:
            print(f"[{i + 1}] 没读到单词，停止（可能已到列表末尾）")
            break
        if word == last_word:
            print(f"[{i + 1}] 单词没变（{word}），停止")
            break
        last_word = word

        if word not in seen:
            rec = {"word": word, "phonetic": phonetic, "meaning": meaning}
            seen[word] = rec
            rows.append(rec)
            with open(jsonl, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[{i + 1}] + {word:<16} {meaning[:40]}")
        else:
            print(f"[{i + 1}] = {word:<16} （已记录，跳过）")

        btn = find_continue(d)
        if not btn:
            print("     找不到「继续」按钮，停止")
            break
        x, y = btn["x"] + btn["w"] // 2, btn["y"] + btn["h"] // 2
        P.s("shell", "input", "tap", str(x), str(y))
        time.sleep(args.wait)

    # 写人类可读的 markdown（全量，不只是本次）
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 词达人词表（{time.strftime('%Y-%m-%d %H:%M')}）\n\n")
        f.write(f"共 {len(seen)} 个词\n\n| 单词 | 音标 | 词义 |\n|---|---|---|\n")
        for w, o in seen.items():
            f.write(f'| {w} | {o["phonetic"]} | {o["meaning"]} |\n')
    print(f"\n本次新增 {len(rows)} 个，累计 {len(seen)} 个")
    print(f"词表：{md_path}")
    print(f"原始记录：{jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
