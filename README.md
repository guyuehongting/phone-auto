# phone-auto · 手机连电脑操控

手机插到电脑上，在电脑上读屏、点击、滑动。三条路线，按需取用。

## 三条路线怎么选

| 路线 | 能做什么 | 需要什么 | 适合 |
|---|---|---|---|
| **scrcpy**（投屏） | 画面投到电脑窗口，鼠标键盘直接操作手机 | 只装 scrcpy（自带 adb） | 手动操作、演示、录屏 |
| **adb + OCR**（本仓库 `phone_adb.py`） | 读屏文字 → 按文字算坐标 → `input tap` 点击 | scrcpy 或任意 adb | 脚本化、定时任务 |
| **Airtest / uiautomator2** | 读控件树（id/文字/类名），按控件操作 | 手机装服务端 APK | 需要精确断言、正式测试 |

> 关键区别：前两条是**按坐标点**，界面一变就失效；第三条是**按控件点**，稳但要多装东西。

## 依赖说明

| 文件 | 需要的依赖 | 说明 |
|---|---|---|
| `phone_adb.py` | **无**（Python 标准库 + scrcpy 自带 adb） | 装好 scrcpy 就能用 |
| `phone.py` / `demo.py` | `pip install airtest` | 走 Airtest 的路线，未安装会报错 |

只走 adb + OCR 路线的话，一条 pip 都不用装。

## 一、手机准备（三条路线通用）

1. 设置 → 关于手机 → 连点「版本号」7 次，出现开发者选项
2. 开发者选项 → 打开 **USB 调试**
3. 数据线连电脑（**必须是能传数据的线**，纯充电线不行）
4. 手机弹出「是否允许 USB 调试」→ 勾选「一律允许」→ 确定
5. 电脑上验证：

```bat
python phone_adb.py devices
```

状态必须是 `device`。出现 `unauthorized` = 手机上没点允许；`offline` = 拔插一次。

## 二、scrcpy：投屏 + 鼠标操控

装好后（`winget install Genymobile.scrcpy`）在终端直接运行：

```bat
scrcpy                  :: 默认参数投屏
scrcpy --max-size 1024  :: 限制分辨率，省带宽
scrcpy --turn-screen-off :: 投屏时关掉手机屏幕（省电）
scrcpy -w               :: 无边框窗口
```

投屏窗口里的常用操作：

| 操作 | 作用 |
|---|---|
| 鼠标左键 | 点击 |
| 按住拖动 | 滑动 |
| 鼠标中键 / 右键 | 返回 / 回桌面 |
| Ctrl+Shift+O | 关手机屏幕 |
| Ctrl+Shift+V | 粘贴电脑剪贴板到手机 |
| Ctrl+Shift+F | 全屏 |

## 三、phone_adb.py：脚本化操控

```bat
:: 看屏幕上有哪些字（截图 + Windows OCR）
python phone_adb.py see
python phone_adb.py see --grep 设置

:: 按文字点击（先 --dry 看候选，别盲点）
python phone_adb.py click "设置" --dry
python phone_adb.py click "设置"

:: 按坐标点 / 滑 / 按键
python phone_adb.py tap 540 1200
python phone_adb.py swipe 540 1600 540 600 400
python phone_adb.py key back

:: 亮屏解锁 / 打开应用
python phone_adb.py unlock
python phone_adb.py app com.android.settings
```

坐标就是**手机截图里的像素点**，不是电脑屏幕上投屏窗口的位置——所以投屏窗口缩放多少都不影响点击。

## 四、中文输入

`adb shell input text` 只支持 ASCII。要输中文，装 [ADBKeyboard](https://github.com/senzhk/ADBKeyBoard) 这个输入法 APK：

```bat
adb install ADBKeyboard.apk
adb shell ime set com.android.adbkeyboard/.AdbIME
```

之后用广播发送中文：

```bat
adb shell am broadcast -a ADB_INPUT_TEXT --es msg "你好世界"
```

## 五、常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `unauthorized` | 手机上没确认调试授权 | 拔插数据线，在手机上点「允许」 |
| 截图成功但全黑 | 视频/银行类应用禁止截屏（FLAG_SECURE） | 无解，换应用测 |
| 投屏有画面但点不动 | 手机锁屏中 | 先 `unlock` 或手动解锁 |
| 点击位置偏了 | 用了电脑屏幕坐标而不是手机截图坐标 | 用 `see` 输出的坐标 |
| 无线调试连不上 | 手机和电脑不在同一网段，或路由器隔离 | 同一 WiFi，或用 `adb pair` 配对码 |
| scrcpy 启动报 server 版本不符 | 电脑和手机 adb 版本冲突 | 统一用 scrcpy 自带的 adb |

## 六、边界

这套工具用于自动化操作自己的设备、自己的账号。对第三方 App 做批量操作通常违反其用户协议，计分作业、考试类场景不在本工具适用范围。

## 七、仓库内容

```
phone_adb.py        读屏 / 点击 / 滑动 / 按键 / 开关应用 / 解锁（零依赖）
verify_click.py     点一次并证明真的点到了：点击前后像素比对 + 返回校验（需 opencv）
collect_words.py    按词卡版式自动翻页、提取单词与释义（按需改选择器）
rebuild_words.py    把采集到的原始记录清洗重建为词表
phone.py / demo.py  Airtest 版本（需 pip install airtest）
ocr.ps1             Windows 自带 OCR 的调用脚本（简体中文可用，输出带坐标的 JSON）
投屏.bat            一键拉起 scrcpy 投屏
```

`shots/`（运行时截图）和 `words/`（采集到的个人词表）已在 `.gitignore` 中排除，不入库。

跑 `verify_click.py` 需要额外装：`pip install opencv-python numpy`。
