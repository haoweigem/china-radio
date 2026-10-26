#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建全国广播电台数据集。

从公开的 m3u 聚合列表抓取原始条目，清洗名称、识别省份与分类、去重，
输出 data/stations.json 供播放器使用。

用法：
    python -X utf8 build_data.py                    # 从默认源抓取
    python -X utf8 build_data.py --source raw.m3u   # 用本地文件
    python -X utf8 build_data.py --check             # 附带抽样连通性检查
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from regions import detect_province, detect_category  # noqa: E402

DEFAULT_SOURCE = "https://raw.githubusercontent.com/zheng-shun/tvbox/master/radio.m3u"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stations.json"

# 只收这几个分组（其余是海外台）
KEEP_GROUPS = {"央广", "地方", "中国广播", "音乐"}

# 第三方整理者加的噪声前缀
NOISE_PREFIXES = ["广通", "阿穆尔河", "希望", "神思", "钢琴", "公共广播", "古典", "中国"]

# 明显非中国电台的关键词（避免误收）
FOREIGN_HINTS = [
    "BBC", "NPR", "CNN", "LBC", "MSNBC", "Al Jazeera", "Singapore", "Malaysia",
    "Mediacorp", "Capital FM", "Class 95", "Gold 905", "Love 972", "Oli 968",
    "Warna", "UFM", "Symphony", "Nightwave", "Listen.Moe", "R/a/dio", "ICRT",
    "NHK", "VOA", "Good TV", "美国之音", "自由亚洲",
]


def fetch(source: str) -> str:
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read().decode("utf-8", "replace")
    return Path(source).read_text(encoding="utf-8", errors="replace")


def parse_m3u(text: str):
    """把 m3u 解析成 (group, name, url) 三元组。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            m = re.search(r'group-title="([^"]*)"', line)
            group = m.group(1) if m else ""
            name = line.split(",", 1)[1].strip() if "," in line else ""
            url = ""
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                url = lines[i + 1].strip()
                i += 1
            out.append((group, name, url))
        i += 1
    return out


def clean_name(name: str):
    """剥离噪声前缀，返回 (干净名称, 前缀省份提示)。

    「中国-北京交通广播」「文学-北京文艺广播」「广通-怀集音乐之声」这类前缀
    要么是整理者加的噪声，要么和后半段的城市矛盾，统一以能识别出地区的后半段为准。
    """
    n = name.strip()
    hint = ""
    for _ in range(3):  # 最多剥三层前缀
        stripped = False
        for sep in ("-", "－", "_", "—", "–"):
            if sep not in n:
                continue
            head, tail = n.split(sep, 1)
            head, tail = head.strip(), tail.strip()
            if not head or not tail:
                continue
            head_prov = detect_province(head + "台", "")
            tail_prov = detect_province(tail, "")
            if head in NOISE_PREFIXES:
                n, stripped = tail, True
            elif head_prov == "其他" and tail_prov != "其他":
                n, stripped = tail, True      # 前缀不是地名，是杂质
            elif head_prov != "其他" and tail_prov not in ("其他", head_prov):
                n, stripped = tail, True      # 前缀省与城市矛盾，信城市
            elif head_prov != "其他":
                hint = head_prov
            if stripped:
                break
        if not stripped:
            break
    n = re.sub(r"^[\s\-－_]+|[\s\-－_]+$", "", n)
    return n, hint


def normalize_key(name: str) -> str:
    """用于去重的归一化名称：去掉频率、空格、标点，以及「广播/电台」这类尾部通名。"""
    n = re.sub(r"(?i)\bFM\s*\d+(\.\d+)?|\bAM\s*\d+(\.\d+)?", "", name)
    n = re.sub(r"[\s·•\-—－–_()（）\[\]【】]", "", n)
    n = re.sub(r"(人民广播电台|广播电台|广播|电台|频率|频道|之声)$", "", n)
    return n.lower()


def stream_kind(url: str) -> str:
    u = url.lower().split("?", 1)[0].split("#", 1)[0]
    if u.endswith((".m3u8", ".m3u")):
        return "hls"
    if u.endswith(".mp3"):
        return "mp3"
    if u.endswith(".aac"):
        return "aac"
    if u.endswith(".ogg"):
        return "ogg"
    if u.endswith(".flv"):
        return "flv"
    return "stream"


UNSUPPORTED = {"flv"}


def build(source: str, do_check: bool = False, sample=None):
    raw = fetch(source)
    triples = parse_m3u(raw)
    print(f"原始条目 {len(triples)}")

    stations = {}
    dropped = {"group": 0, "foreign": 0, "unsupported": 0, "empty": 0}

    for group, name, url in triples:
        if group not in KEEP_GROUPS:
            dropped["group"] += 1
            continue
        if not url or not name:
            dropped["empty"] += 1
            continue
        if any(h.lower() in name.lower() for h in FOREIGN_HINTS):
            dropped["foreign"] += 1
            continue
        kind = stream_kind(url)
        if kind in UNSUPPORTED:
            dropped["unsupported"] += 1
            continue

        clean, hint = clean_name(name)
        if not clean:
            dropped["empty"] += 1
            continue
        province = hint or detect_province(clean, group)
        category = detect_category(clean)

        key = (normalize_key(clean), province)
        if key not in stations:
            stations[key] = {
                "n": clean,
                "p": province,
                "c": category,
                "urls": [],
            }
        elif len(clean) > len(stations[key]["n"]):
            stations[key]["n"] = clean  # 保留信息更完整的写法（常带频率）
        if url not in stations[key]["urls"]:
            stations[key]["urls"].append(url)

    # 每个台选主源：mp3 优先（浏览器原生支持），其次 hls
    final = []
    for (name, province), st in stations.items():
        urls = sorted(st["urls"], key=lambda u: 0 if stream_kind(u) == "mp3" else 1)
        main = urls[0]
        final.append({
            "n": st["n"],
            "p": st["p"],
            "c": st["c"],
            "u": main,
            "t": stream_kind(main),
            "alt": urls[1:3],
        })

    # 排序：中央 → 按省份 → 按分类
    order = ["中央"] + [p for p in _province_order()]
    final.sort(key=lambda s: (
        order.index(s["p"]) if s["p"] in order else 999,
        s["c"],
        s["n"],
    ))

    stats_p, stats_c = {}, {}
    for s in final:
        stats_p[s["p"]] = stats_p.get(s["p"], 0) + 1
        stats_c[s["c"]] = stats_c.get(s["c"], 0) + 1

    data = {
        "meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "count": len(final),
            "dropped": dropped,
            "note": "公共广播流，仅供个人收听；版权归各电台所有。",
        },
        "stats": {"by_province": stats_p, "by_category": stats_c},
        "stations": final,
    }

    if do_check:
        result = check_streams(final, sample=sample)
        dead_set = set(result.pop("dead_urls", []))
        if result["sampled"] == len(final):
            for s in final:
                s["ok"] = s["u"] not in dead_set
        data["meta"]["check"] = result

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def _province_order():
    return [
        "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
        "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
        "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
        "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆",
        "中国香港", "中国澳门", "中国台湾", "其他",
    ]


def probe(url, timeout=8):
    """探测单个流是否可连。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            chunk = r.read(2048)
            return url, bool(chunk), r.status
    except Exception as exc:
        return url, False, type(exc).__name__


def check_streams(stations, sample=None):
    """并发检查流可用性，返回统计和失效 URL 明细。"""
    urls = [s["u"] for s in stations]
    if sample and 0 < sample < len(urls):
        step = max(1, len(urls) // sample)
        urls = urls[::step][:sample]
    print(f"检测 {len(urls)} 条流…")
    ok = 0
    dead = []
    with ThreadPoolExecutor(max_workers=32) as pool:
        for url, good, info in pool.map(probe, urls):
            if good:
                ok += 1
            else:
                dead.append(url)
    return {
        "sampled": len(urls),
        "alive": ok,
        "dead": len(dead),
        "dead_urls": dead,
        "dead_examples": dead[:15],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=DEFAULT_SOURCE)
    ap.add_argument("--check", action="store_true", help="抽样检测流连通性")
    ap.add_argument("--sample", type=int, default=0, help="检测抽样条数，0=全量")
    args = ap.parse_args()

    data = build(args.source, do_check=args.check, sample=args.sample if args.sample > 0 else None)
    meta = data["meta"]
    print(f"清洗后 {meta['count']} 个电台，丢弃：{meta['dropped']}")
    print("省市分布：")
    for p, n in sorted(data["stats"]["by_province"].items(), key=lambda kv: -kv[1]):
        print(f"  {p}: {n}")
    print("分类分布：", data["stats"]["by_category"])
    if "check" in meta:
        print("连通性：", meta["check"]["alive"], "/", meta["check"]["sampled"], "可用")
    print(f"已写入 {OUT}")


if __name__ == "__main__":
    main()
