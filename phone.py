"""
手机自动化封装（Airtest + ADB）
================================
把 Airtest 的常用操作包成命令行，方便逐步验证"手机到底连上没有、能不能点"。

命令：
    python phone.py check                    # 环境自检（adb / 设备 / 授权）
    python phone.py list                     # 列出已连接设备
    python phone.py shot out.png             # 截屏存文件
    python phone.py info                     # 屏幕分辨率 / 当前应用
    python phone.py tap 540 1200             # 点击坐标
    python phone.py longpress 540 1200 800   # 长按 800ms
    python phone.py swipe 540 1600 540 600 400
    python phone.py text "hello"             # 输入（英文）
    python phone.py key home                 # home/back/recent/enter
    python phone.py app com.android.settings # 启动应用
    python phone.py find tpl.png --tap       # 图像识别找模板并点击

坐标一律是**手机截图上的像素坐标**，不是电脑屏幕坐标。
"""

import argparse
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TPL_DIR = os.path.join(BASE_DIR, "templates")
SHOT_DIR = os.path.join(BASE_DIR, "shots")


def _adb_path():
    """Airtest 自带 adb，免装 Android SDK"""
    try:
        import airtest
        p = os.path.join(os.path.dirname(airtest.__file__),
                         "core", "android", "static", "adb", "windows", "adb.exe")
        if os.path.exists(p):
            return p
    except Exception:
        pass
    return "adb"


def adb(args, timeout=20):
    cmd = [_adb_path()] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except FileNotFoundError:
        return "", "找不到 adb（airtest 未安装？）", -1
    except subprocess.TimeoutExpired:
        return "", "adb 超时", -2


def list_devices():
    out, err, rc = adb(["devices", "-l"])
    if rc != 0:
        print("adb 执行失败：", err)
        return []
    lines = [l for l in out.splitlines()[1:] if l.strip()]
    devs = []
    for l in lines:
        parts = l.split()
        serial, state = parts[0], parts[1] if len(parts) > 1 else ""
        model = ""
        for p in parts[2:]:
            if p.startswith("model:"):
                model = p.split(":", 1)[1]
        devs.append({"serial": serial, "state": state, "model": model})
    return devs


def cmd_check(args):
    print("=== 环境自检 ===")
    try:
        import airtest
        print(f"airtest 版本：{airtest.__version__}")
    except Exception as e:
        print(f"airtest 未安装：{e}")
        return 1
    print(f"adb 路径：{_adb_path()}")
    out, err, rc = adb(["version"])
    print(f"adb 版本：{out.splitlines()[0] if out else err}")

    devs = list_devices()
    if not devs:
        print("\n没有检测到设备。请依次确认：")
        print("  1. 手机用数据线连电脑（有的线只能充电，不能传数据）")
        print("  2. 设置 → 关于手机 → 连点版本号 7 次，开开发者选项")
        print("  3. 开发者选项 → USB 调试 打开")
        print("  4. 手机上弹出「允许 USB 调试吗」→ 勾选一律允许 → 确定")
        print("  5. 重新运行本命令")
        return 2

    for d in devs:
        state = d["state"]
        flag = {"device": "已授权，可用",
                "unauthorized": "未授权（手机上没点允许）",
                "offline": "离线（拔插一下或 adb kill-server）",
                "no permissions": "权限不足（Windows 驱动问题）"}.get(state, state)
        print(f'  {d["serial"]:<24} {d["model"]:<16} {state:<14} {flag}')
    ok = any(d["state"] == "device" for d in devs)
    print("\n结论：", "可以开始自动化" if ok else "设备存在但不可用，按上面提示处理")
    return 0 if ok else 3


def cmd_list(_args):
    devs = list_devices()
    if not devs:
        print("没有设备")
        return 1
    for d in devs:
        print(f'{d["serial"]:<24} {d["model"]:<16} {d["state"]}')
    return 0


def connect(silent=False):
    """连接第一台可用设备，返回 airtest 设备对象"""
    from airtest.core.api import connect_device
    devs = [d for d in list_devices() if d["state"] == "device"]
    if not devs:
        raise RuntimeError("没有可用设备，先运行 python phone.py check")
    uri = f'Android:///{devs[0]["serial"]}'
    if not silent:
        print(f"连接 {uri}")
    return connect_device(uri)


def cmd_shot(args):
    dev = connect()
    path = args.path
    if not os.path.isabs(path):
        os.makedirs(SHOT_DIR, exist_ok=True)
        path = os.path.join(SHOT_DIR, path)
    from airtest.core.api import snapshot
    snapshot(filename=path)
    print(f"已保存 {path}")
    return 0


def cmd_info(args):
    dev = connect()
    w, h = dev.get_current_resolution()
    print(f"分辨率 {w}x{h}")
    out, _, _ = adb(["-s", list_devices()[0]["serial"], "shell", "dumpsys", "window", "|", "grep", "mCurrentFocus"])
    # grep 需要通过 shell 管道，这里退化为直接读
    out2, _, _ = adb(["-s", list_devices()[0]["serial"], "shell", "dumpsys window windows"])
    for line in out2.splitlines():
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            print(line.strip())
    return 0


def cmd_tap(args):
    dev = connect()
    from airtest.core.api import touch
    touch((args.x, args.y))
    print(f"已点击 ({args.x},{args.y})")
    return 0


def cmd_longpress(args):
    dev = connect()
    from airtest.core.api import long_click
    long_click((args.x, args.y), duration=args.ms / 1000.0)
    print(f"已长按 ({args.x},{args.y}) {args.ms}ms")
    return 0


def cmd_swipe(args):
    dev = connect()
    from airtest.core.api import swipe
    swipe((args.x1, args.y1), (args.x2, args.y2), duration=args.ms / 1000.0)
    print(f"已滑动 ({args.x1},{args.y1}) -> ({args.x2},{args.y2})")
    return 0


def cmd_text(args):
    dev = connect()
    from airtest.core.api import text as atext
    atext(args.text)
    print(f"已输入 {args.text}")
    return 0


def cmd_key(args):
    dev = connect()
    from airtest.core.api import keyevent
    mapping = {"home": "HOME", "back": "BACK", "recent": "APP_SWITCH", "enter": "ENTER"}
    k = mapping.get(args.name.lower(), args.name.upper())
    keyevent(k)
    print(f"已按键 {k}")
    return 0


def cmd_app(args):
    dev = connect()
    from airtest.core.api import start_app, stop_app
    if args.stop:
        stop_app(args.package)
        print(f"已停止 {args.package}")
    else:
        start_app(args.package)
        print(f"已启动 {args.package}")
    return 0


def cmd_find(args):
    """截图 + 模板匹配，可选直接点击"""
    import cv2
    import numpy as np
    dev = connect()
    from airtest.core.api import snapshot, touch

    os.makedirs(SHOT_DIR, exist_ok=True)
    shot = os.path.join(SHOT_DIR, "find_shot.png")
    snapshot(filename=shot)
    frame = cv2.imdecode(np.fromfile(shot, dtype=np.uint8), cv2.IMREAD_COLOR)
    tpl_path = args.template if os.path.isabs(args.template) else os.path.join(TPL_DIR, args.template)
    tpl = cv2.imdecode(np.fromfile(tpl_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if tpl is None:
        print(f"读不到模板 {tpl_path}")
        return 1
    if tpl.shape[0] > frame.shape[0] or tpl.shape[1] > frame.shape[1]:
        print("模板比屏幕还大，检查是不是不同分辨率下截的")
        return 1

    gf = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gt = cv2.cvtColor(tpl, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(gf, gt, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res, nan=-1)
    _, mx, _, ml = cv2.minMaxLoc(res)
    x, y = ml
    w, h = tpl.shape[1], tpl.shape[0]
    print(f"相似度 {mx:.3f}  位置 ({x},{y}) 尺寸 {w}x{h}")
    if mx < args.threshold:
        print(f"低于阈值 {args.threshold}，不点击")
        return 2
    if args.tap:
        touch((x + w // 2, y + h // 2))
        print(f"已点击 ({x + w // 2},{y + h // 2})")
    return 0


def main():
    ap = argparse.ArgumentParser(description="手机自动化（Airtest 封装）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sub.add_parser("info").set_defaults(func=cmd_info)

    p = sub.add_parser("shot"); p.add_argument("path", nargs="?", default="shot.png"); p.set_defaults(func=cmd_shot)

    p = sub.add_parser("tap"); p.add_argument("x", type=int); p.add_argument("y", type=int); p.set_defaults(func=cmd_tap)

    p = sub.add_parser("longpress")
    p.add_argument("x", type=int); p.add_argument("y", type=int)
    p.add_argument("ms", type=int, nargs="?", default=800); p.set_defaults(func=cmd_longpress)

    p = sub.add_parser("swipe")
    for n in ("x1", "y1", "x2", "y2"):
        p.add_argument(n, type=int)
    p.add_argument("ms", type=int, nargs="?", default=400); p.set_defaults(func=cmd_swipe)

    p = sub.add_parser("text"); p.add_argument("text"); p.set_defaults(func=cmd_text)

    p = sub.add_parser("key"); p.add_argument("name"); p.set_defaults(func=cmd_key)

    p = sub.add_parser("app"); p.add_argument("package"); p.add_argument("--stop", action="store_true"); p.set_defaults(func=cmd_app)

    p = sub.add_parser("find")
    p.add_argument("template")
    p.add_argument("--tap", action="store_true")
    p.add_argument("--threshold", type=float, default=0.8)
    p.set_defaults(func=cmd_find)

    args = ap.parse_args()
    os.makedirs(TPL_DIR, exist_ok=True)
    os.makedirs(SHOT_DIR, exist_ok=True)
    try:
        return args.func(args)
    except RuntimeError as e:
        print(f"失败：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
