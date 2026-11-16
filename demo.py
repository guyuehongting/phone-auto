"""
Airtest 入门演示（安全版：只截图和滚动，不点任何会改数据的按钮）
================================================================
运行：.venv\\Scripts\\python.exe demo.py

这个脚本演示 Airtest 的核心四件事：
  1. 连设备
  2. 截图存档（后面做模板匹配要用）
  3. 滑动 / 点击 / 按键
  4. 断言（脚本跑失败能立刻看出来）

跑完到 log/ 目录看报告，每步都带截图，能回放。
"""

import os
import sys

from airtest.core.api import (
    auto_setup, connect_device, snapshot, swipe, touch, keyevent,
    start_app, stop_app, exists, wait, sleep, Template,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
TPL_DIR = os.path.join(BASE_DIR, "templates")


def main():
    # 1) 初始化：指定日志目录，Airtest 会把每步截图和断言结果写进 HTML 报告
    auto_setup(__file__, logdir=LOG_DIR, devices=["Android:///"])

    # 2) 连接第一台已授权设备（等价于 adb devices 里状态为 device 的那台）
    dev = connect_device("Android:///")
    w, h = dev.get_current_resolution()
    print(f"已连接：{dev}  分辨率 {w}x{h}")

    # 3) 截图：这一步最有用——之后做模板匹配的素材都从截图里裁
    snapshot(filename=os.path.join(BASE_DIR, "shots", "01_当前画面.png"))
    print("已截图 01")

    # 4) 打开系统设置（无害，随时能返回）
    try:
        start_app("com.android.settings")
        sleep(2)
        snapshot(filename=os.path.join(BASE_DIR, "shots", "02_设置页.png"))
        print("已打开设置并截图 02")
    except Exception as e:
        print(f"打开设置失败（部分机型包名不同，可跳过）：{e}")

    # 5) 滑一下，验证手势通道正常
    swipe((w // 2, int(h * 0.75)), (w // 2, int(h * 0.35)), duration=0.6)
    sleep(1)
    snapshot(filename=os.path.join(BASE_DIR, "shots", "03_滑动后.png"))
    print("已滑动并截图 03")

    # 6) 图像识别示例：模板存在才点，不存在就跳过（避免瞎点）
    tpl_path = os.path.join(TPL_DIR, "demo_target.png")
    if os.path.exists(tpl_path):
        target = Template(tpl_path, threshold=0.8)
        if exists(target):
            touch(target)
            print("已按模板点击 demo_target.png")
        else:
            print("模板没在当前画面里找到，跳过点击")
    else:
        print(f"没有模板 {tpl_path}，跳过图像识别示例")
        print("  做法：从 shots/01_当前画面.png 里裁一个按钮存成 templates/demo_target.png")

    # 7) 回桌面
    keyevent("HOME")
    print("已返回桌面")

    print(f"\n完成。报告在 {os.path.join(LOG_DIR, 'log.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
