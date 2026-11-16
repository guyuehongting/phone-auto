"""
手机操控（scrcpy 自带 adb + Windows OCR）
==========================================
不依赖 Airtest：全部走 adb 三条命令
    读屏   adb exec-out screencap -p
    看字   Windows OCR（ocr.ps1）
    点击   adb shell input tap x y

这条链路的好处：手机不用装任何 App、不用 root，插上线就能用；
缺点是只能按坐标点，读不到控件树（要控件树得上 uiautomator2）。

命令：
    python phone_adb.py devices                  # 列设备
    python phone_adb.py shot                     # 截图（存 shots/phone.png）
    python phone_adb.py see                      # 截图 + OCR，打印屏幕上的文字和坐标
    python phone_adb.py see --grep 设置
    python phone_adb.py tap 540 1200             # 按坐标点
    python phone_adb.py click "设置" --dry        # 按文字找位置（先只看不点）
    python phone_adb.py click "设置"
    python phone_adb.py swipe 540 1600 540 600 400
    python phone_adb.py key home|back|enter|power
    python phone_adb.py text "hello"             # 只能英文；中文见 README
    python phone_adb.py app com.android.settings # 打开应用
    python phone_adb.py unlock                   # 亮屏并上滑解锁
"""

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHOT_DIR = os.path.join(BASE_DIR, "shots")
OCR_PS1 = os.path.join(BASE_DIR, "ocr.ps1")


# ------------------------------------------------------------------ adb 定位
def find_adb():
    """依次在环境变量、PATH、scrcpy 安装目录、Airtest 目录里找 adb"""
    cand = []
    if os.environ.get("ADB"):
        cand.append(os.environ["ADB"])
    w = shutil.which("adb")
    if w:
        cand.append(w)

    pkg_root = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    if os.path.isdir(pkg_root):
        for d in os.listdir(pkg_root):
            if "scrcpy" in d.lower():
                for root, _dirs, files in os.walk(os.path.join(pkg_root, d)):
                    if "adb.exe" in files:
                        cand.append(os.path.join(root, "adb.exe"))
    cand += [
        r"C:\Program Files\Genymobile\scrcpy\adb.exe",
        r"C:\Program Files (x86)\Genymobile\scrcpy\adb.exe",
    ]
    for p in cand:
        if p and os.path.exists(p):
            return p
    return "adb"


ADB = find_adb()


def adb(args, timeout=25, binary=False):
    cmd = [ADB] + args
    if binary:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="ignore", timeout=timeout)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def devices():
    out, err, rc = adb(["devices"])
    if rc != 0:
        raise RuntimeError(f"adb 执行失败：{err or out}\nadb 路径：{ADB}")
    res = []
    for line in out.splitlines()[1:]:
        if line.strip():
            parts = line.split()
            res.append({"serial": parts[0], "state": parts[1] if len(parts) > 1 else ""})
    return res


def serial():
    devs = [d for d in devices() if d["state"] == "device"]
    if not devs:
        raise RuntimeError("没有可用设备：请确认数据线可传数据、已开 USB 调试、手机上已点允许")
    return devs[0]["serial"]


def s(*args):
    """带 -s 的 adb 调用"""
    return adb(["-s", serial()] + list(args))


# ------------------------------------------------------------------ 基础动作
def cmd_devices(_args):
    print(f"adb: {ADB}")
    for d in devices():
        flag = {"device": "可用", "unauthorized": "未授权（手机上点允许）",
                "offline": "离线（拔插或 adb kill-server）"}.get(d["state"], d["state"])
        print(f'  {d["serial"]:<24} {d["state"]:<14} {flag}')
    return 0


def cmd_shot(args):
    os.makedirs(SHOT_DIR, exist_ok=True)
    path = args.path if os.path.isabs(args.path) else os.path.join(SHOT_DIR, args.path)
    data, err, rc = adb(["-s", serial(), "exec-out", "screencap", "-p"], binary=True)
    if rc != 0 or not data.startswith(b"\x89PNG"):
        print(f"截图失败：{err}")
        return 1
    with open(path, "wb") as f:
        f.write(data)
    print(f"已保存 {path}（{len(data) // 1024} KB）")
    return 0


def ocr_image(path):
    out = os.path.join(SHOT_DIR, "ocr.json")
    if os.path.exists(out):
        os.remove(out)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", OCR_PS1, "-Path", path, "-Out", out],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if not os.path.exists(out):
        raise RuntimeError(f"OCR 失败：{(r.stderr or r.stdout)[:300]}")
    with open(out, encoding="utf-8-sig") as f:
        return json.load(f)


def norm(t):
    return re.sub(r"\s+", "", t or "")


def match_lines(data, kw, threshold=0.55):
    k = norm(kw)
    res = []
    for ln in data.get("lines", []):
        t = norm(ln["text"])
        if not t:
            continue
        if t == k:
            sc = 1.0
        elif k in t:
            sc = 0.9 + 0.1 * len(k) / max(len(t), 1)
        else:
            sc = difflib.SequenceMatcher(None, k, t).ratio()
        if sc >= threshold:
            res.append({**ln, "score": round(sc, 3)})
    res.sort(key=lambda d: (-d["score"], d["y"], d["x"]))
    return res


def cmd_see(args):
    cmd_shot(argparse.Namespace(path="phone.png"))
    png = os.path.join(SHOT_DIR, "phone.png")
    data = ocr_image(png)
    print(f'OCR {data["count"]} 行  画布 {data["width"]}x{data["height"]}')
    lines = match_lines(data, args.grep, 0.3) if args.grep else data.get("lines", [])
    for ln in lines[:args.limit]:
        print(f'  [{ln["x"]:>5},{ln["y"]:>5} {ln["w"]:>4}x{ln["h"]:<3}] {ln["text"]}'
              + (f'  (匹配 {ln["score"]})' if "score" in ln else ""))
    return 0


def cmd_tap(args):
    s("shell", "input", "tap", str(args.x), str(args.y))
    print(f"已点击 ({args.x},{args.y})")
    return 0


def cmd_click(args):
    cmd_shot(argparse.Namespace(path="phone.png"))
    data = ocr_image(os.path.join(SHOT_DIR, "phone.png"))
    cands = match_lines(data, args.text, args.threshold)
    if not cands:
        print(f'屏幕上没有「{args.text}」')
        for ln in data.get("lines", [])[:30]:
            print(f'  [{ln["x"]},{ln["y"]}] {ln["text"]}')
        return 2
    print(f"候选 {len(cands)} 个：")
    for i, c in enumerate(cands[:6]):
        print(f'  #{i} {c["score"]} ({c["x"]},{c["y"]},{c["w"]}x{c["h"]}) {c["text"]}')
    if len(cands) > 1 and cands[0]["score"] - cands[1]["score"] < 0.03 and args.index is None:
        print("前两名接近，用 --index 指定")
        return 3
    c = cands[args.index or 0]
    x = c["x"] + c["w"] // 2 + args.dx
    y = c["y"] + c["h"] // 2 + args.dy
    print(f'目标「{c["text"]}」-> ({x},{y})')
    if args.dry:
        print("dry，不点")
        return 0
    s("shell", "input", "tap", str(x), str(y))
    print("已点击")
    return 0


def cmd_swipe(args):
    s("shell", "input", "swipe", str(args.x1), str(args.y1), str(args.x2), str(args.y2), str(args.ms))
    print("已滑动")
    return 0


def cmd_key(args):
    m = {"home": 3, "back": 4, "recent": 187, "enter": 66, "power": 26,
         "volumeup": 24, "volumedown": 25, "menu": 82}
    code = m.get(args.name.lower())
    if code is None:
        print(f"不认识 {args.name}，可用：{','.join(m)}")
        return 1
    s("shell", "input", "keyevent", str(code))
    print(f"已按键 {args.name}")
    return 0


def cmd_text(args):
    if any(ord(ch) > 127 for ch in args.text):
        print("adb input text 不支持中文。中文输入要用 ADBKeyboard 输入法（见 README）")
        return 1
    s("shell", "input", "text", args.text.replace(" ", "%s"))
    print(f"已输入 {args.text}")
    return 0


def cmd_app(args):
    s("shell", "monkey", "-p", args.package, "-c", "android.intent.category.LAUNCHER", "1")
    print(f"已启动 {args.package}")
    return 0


def cmd_unlock(_args):
    s("shell", "input", "keyevent", "224")   # 亮屏
    time.sleep(0.4)
    s("shell", "input", "keyevent", "82")    # 菜单键唤醒
    time.sleep(0.3)
    s("shell", "input", "swipe", "540", "1800", "540", "800", "300")
    print("已尝试亮屏解锁（有密码需要手工输入）")
    return 0


def main():
    ap = argparse.ArgumentParser(description="手机操控（adb + OCR）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("devices").set_defaults(func=cmd_devices)

    p = sub.add_parser("shot"); p.add_argument("path", nargs="?", default="phone.png"); p.set_defaults(func=cmd_shot)

    p = sub.add_parser("see")
    p.add_argument("--grep", default="")
    p.add_argument("--limit", type=int, default=60)
    p.set_defaults(func=cmd_see)

    p = sub.add_parser("tap"); p.add_argument("x", type=int); p.add_argument("y", type=int); p.set_defaults(func=cmd_tap)

    p = sub.add_parser("click")
    p.add_argument("text")
    p.add_argument("--index", type=int)
    p.add_argument("--threshold", type=float, default=0.55)
    p.add_argument("--dx", type=int, default=0)
    p.add_argument("--dy", type=int, default=0)
    p.add_argument("--dry", action="store_true")
    p.set_defaults(func=cmd_click)

    p = sub.add_parser("swipe")
    for n in ("x1", "y1", "x2", "y2"):
        p.add_argument(n, type=int)
    p.add_argument("ms", type=int, nargs="?", default=400)
    p.set_defaults(func=cmd_swipe)

    p = sub.add_parser("key"); p.add_argument("name"); p.set_defaults(func=cmd_key)

    p = sub.add_parser("text"); p.add_argument("text"); p.set_defaults(func=cmd_text)

    p = sub.add_parser("app"); p.add_argument("package"); p.set_defaults(func=cmd_app)

    sub.add_parser("unlock").set_defaults(func=cmd_unlock)

    args = ap.parse_args()
    os.makedirs(SHOT_DIR, exist_ok=True)
    try:
        return args.func(args)
    except RuntimeError as e:
        print(f"失败：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
