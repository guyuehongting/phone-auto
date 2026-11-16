"""按整理好的词表重建 words.jsonl 与词表_单元1.md（一次性脚本，可重复运行）"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "words")
os.makedirs(OUT, exist_ok=True)

# (单词, 音标, 词义, 记忆点)
WORDS = [
    ("sector", "/ˈsektə(r)/", "n. 部门；行业；领域", "拉丁 secare 切 → 切出来的一块"),
    ("embark", "/ɪmˈbɑːk/", "v. 上（船）；开始从事", "em 进入 + bark 船 → 上船启程"),
    ("issue", "/ˈɪʃuː/", "n. 问题；议题", "古法语 issue 出口 → 冒出来的事"),
    ("remote", "/rɪˈməʊt/", "adj. 偏僻的；遥远的", "re 回 + mot 移动 → 移得很远"),
    ("initiative", "/ɪˈnɪʃətɪv/", "n. 倡议；新方案", "in + it 走 → 走在众人前面"),
    ("journalist", "/ˈdʒɜːnəlɪst/", "n. 新闻记者", "journal 日报 + ist 人"),
    ("manufacture", "/ˌmænjuˈfæktʃə(r)/", "v. 制造，生产", "manu 手 + fact 做"),
    ("workshop", "/ˈwɜːkʃɒp/", "n. 车间；工场；作坊", "work + shop 干活的棚子"),
    ("banking", "/ˈbæŋkɪŋ/", "n. 银行业", "bank 银行 + ing"),
    ("economic", "/ˌiːkəˈnɒmɪk/", "adj. 经济（上）的", "eco 家 + nom 管理 → 管家之学"),
    ("trend", "/trend/", "n. 趋势；倾向；动向", "古英语 trendan 旋转 → 转向"),
    ("academic", "/ˌækəˈdemɪk/", "adj. 教学的，学业的", "academy 学园 + ic"),
    ("focus", "/ˈfəʊkəs/", "v. 集中（注意力）；关注", "拉丁“炉灶/焦点” → 光聚一点"),
    ("fare", "/feə(r)/", "n. 旅费；路费；车费", "古英语 faran 行走 → 出行的钱"),
    ("investment", "/ɪnˈvestmənt/", "n. 投资（额）", "in + vest 衣服 → 给钱穿衣去生钱"),
    ("stem", "/stem/", "n.（植物的）干，茎", "动词义：stem from 源于；stem 阻止"),
    ("contribute", "/kənˈtrɪbjuːt/", "v. 捐献；援助", "con 共同 + tribut 给"),
    ("artificial", "/ˌɑːtɪˈfɪʃl/", "adj. 人工的；人造的", "arti 技艺 + fic 做"),
    ("retail", "/ˈriːteɪl/", "n. 零售；零卖", "re 再 + tail 切 → 切碎了卖"),
    ("convertible", "/kənˈvɜːtəbl/", "adj.（货币）可兑换的", "con + vert 转 + ible 可…的"),
    ("prompt", "/prɒmpt/", "adj. 迅速的；及时的", "拉丁 promptus 准备好的；v. 提示"),
    ("transform", "/trænsˈfɔːm/", "v. 转换；改造；使彻底改观", "trans 变 + form 形状 → 变形"),
    ("inflation", "/ɪnˈfleɪʃn/", "n. 通货膨胀", "in 向内 + flat 吹 + ion → 吹起来"),
    ("mega", "/ˈmeɡə/", "adj. 巨大的；极佳的", "希腊 megas 大；口语“超赞”"),
    ("compromise", "/ˈkɒmprəmaɪz/", "n. 折中；妥协；让步", "com 共同 + promise 承诺 → 各退一步"),
    ("grim", "/ɡrɪm/", "adj. 严肃的；严酷的", "grim 也指“阴沉、grim reality 严峻现实”"),
    ("overnight", "/ˌəʊvəˈnaɪt/", "adv. 在夜间；一夜之间", "over + night"),
    ("overtake", "/ˌəʊvəˈteɪk/", "v. 追上，超越", "over 越过 + take"),
    ("accelerate", "/əkˈseləreɪt/", "v.（使）加快；（使）增速", "ac 加强 + celer 快 + ate"),
    ("considerably", "/kənˈsɪdərəbli/", "adv. 相当地，极大地", "consider 考虑 + able → 值得考虑的 → 相当"),
    ("permanently", "/ˈpɜːmənəntli/", "adv. 永久地；持久地", "per 贯穿 + man 停留"),
    ("hive", "/haɪv/", "n. 蜂房；蜂箱", "hive mind 群体思维"),
    ("flourish", "/ˈflʌrɪʃ/", "v. 繁荣；兴旺", "flor 花 + ish → 开花 → 兴盛"),
]

with open(os.path.join(OUT, "words.jsonl"), "w", encoding="utf-8") as f:
    for w, ph, mn, _memo in WORDS:
        f.write(json.dumps({"word": w, "phonetic": ph, "meaning": mn}, ensure_ascii=False) + "\n")

md = ["# 词达人 · 词表（2026-11-17 自动采集 33 词）", "",
      "采集方式：手机投屏 + Windows OCR 自动翻词卡（`collect_words.py`）。原始数据 `words.jsonl`。", "",
      "> OCR 修正：ISSue→issue、e CO n 0 m ℃→economic、compromnse→compromise、grlm→grim；例句页被误当单词，已剔除。", "",
      "| # | 单词 | 音标 | 词性/词义 | 记忆点 |", "|---|---|---|---|---|"]
for i, (w, ph, mn, memo) in enumerate(WORDS, 1):
    md.append(f"| {i} | {w} | {ph} | {mn} | {memo} |")

md += ["", "## 易混提醒", "",
       "- **economic / economical**：经济的 / 节约的（an economical car）",
       "- **issue / problem**：issue 偏议题，problem 偏故障难题",
       "- **fare / fee / charge**：交通费 / 服务会费 / 一次性收费",
       "- **compromise 两个方向**：作名词“妥协”，作动词“危及（compromise safety）”",
       "- **prompt**：形容词“迅速的”和动词“提示/促使”，考试两个义项都考",
       "- **stem**：名词“茎”，动词“源于（stem from）/ 阻止”"]

with open(os.path.join(OUT, "词表_单元1.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"已写入 {len(WORDS)} 个词")
print(os.path.join(OUT, "词表_单元1.md"))
