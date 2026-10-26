#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全国广播电台：查询与播放页生成。

    python -X utf8 radio.py stats
    python -X utf8 radio.py provinces
    python -X utf8 radio.py list --province 广东 --category 交通
    python -X utf8 radio.py list --search 哈尔滨
    python -X utf8 radio.py page --province 四川 --out ./sichuan.html
    python -X utf8 radio.py page --category 音乐 --title "音乐电台"
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "stations.json"
TEMPLATE = ROOT / "assets" / "player_template.html"
HLS_JS = ROOT / "assets" / "hls.min.js"


def load():
    if not DATA.exists():
        raise SystemExit(f"缺少数据文件 {DATA}\n先运行：python -X utf8 build_data.py --check")
    return json.loads(DATA.read_text(encoding="utf-8"))


def select(data, province=None, category=None, search=None, only_ok=False):
    out = []
    q = (search or "").strip().lower()
    for s in data["stations"]:
        if province and s["p"] != province:
            continue
        if category and s["c"] != category:
            continue
        if only_ok and s.get("ok") is False:
            continue
        if q and q not in s["n"].lower() and q not in s["p"].lower():
            continue
        out.append(s)
    return out


def cmd_stats(args):
    data = load()
    meta = data["meta"]
    print(f"共 {meta['count']} 个电台｜生成于 {meta['generated']}")
    chk = meta.get("check")
    if chk and chk.get("sampled", 0) >= meta["count"]:
        rate = chk["alive"] / max(1, chk["sampled"]) * 100
        print(f"全量连通检测：{chk['alive']}/{chk['sampled']} 可用（{rate:.0f}%）")
    print("\n分类：")
    for c, n in sorted(data["stats"]["by_category"].items(), key=lambda kv: -kv[1]):
        print(f"  {c:<6} {n:>4}")
    print("\n省份（前 12）：")
    for p, n in sorted(data["stats"]["by_province"].items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {p:<8} {n:>4}")


def cmd_provinces(args):
    data = load()
    stats = data["stats"]["by_province"]
    for p, n in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"{p:<10} {n:>4}")


def cmd_categories(args):
    data = load()
    for c, n in sorted(data["stats"]["by_category"].items(), key=lambda kv: -kv[1]):
        print(f"{c:<8} {n:>4}")


def cmd_list(args):
    data = load()
    rows = select(data, args.province, args.category, args.search, args.only_ok)
    if not rows:
        print("没有匹配的电台。")
        return 1
    limit = args.limit or len(rows)
    for s in rows[:limit]:
        flag = "" if s.get("ok") is not False else "  (上次检测未连通)"
        print(f"{s['n']}  [{s['p']} · {s['c']} · {s['t']}]{flag}")
    if len(rows) > limit:
        print(f"\n… 共 {len(rows)} 个，已显示前 {limit} 个（用 --limit 调整）")
    else:
        print(f"\n共 {len(rows)} 个")
    return 0


def cmd_page(args):
    data = load()
    rows = select(data, args.province, args.category, args.search, args.only_ok)
    if not rows:
        print("没有匹配的电台，换个条件试试。")
        return 1
    if args.limit:
        rows = rows[: args.limit]

    # 上次检测连通的排前面（稳定排序，其余保持原来的省份/分类顺序）
    rows = sorted(rows, key=lambda s: 0 if s.get("ok") is not False else 1)

    template = TEMPLATE.read_text(encoding="utf-8")
    hls_js = HLS_JS.read_text(encoding="utf-8", errors="replace") if HLS_JS.exists() else ""

    payload = [
        {"n": s["n"], "p": s["p"], "c": s["c"], "u": s["u"], "t": s["t"], "ok": s.get("ok")}
        for s in rows
    ]
    prov_stats = {}
    for s in rows:
        prov_stats[s["p"]] = prov_stats.get(s["p"], 0) + 1

    if args.title:
        title = args.title
    else:
        bits = [args.province, args.category, args.search]
        title = "全国广播电台" + (" · " + " · ".join(b for b in bits if b) if any(bits) else "")

    html = (template
            .replace("__TITLE__", title)
            .replace("__STATIONS__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__PROV_STATS__", json.dumps(prov_stats, ensure_ascii=False))
            .replace("__HLS_JS__", hls_js))

    out = Path(args.out).expanduser().resolve() if args.out else ROOT / "data" / "player.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"已生成播放页：{out}")
    print(f"收录 {len(rows)} 个电台，打开后点卡片即可收听（HLS 流已在页面内置解码）。")
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(prog="radio.py", description="全国广播电台查询与播放页")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stats", help="数据概览")
    s.set_defaults(func=cmd_stats)

    p = sub.add_parser("provinces", help="各省电台数")
    p.set_defaults(func=cmd_provinces)

    c = sub.add_parser("categories", help="各分类电台数")
    c.set_defaults(func=cmd_categories)

    li = sub.add_parser("list", help="列出电台")
    li.add_argument("--province", help="省份，如 广东 / 中央")
    li.add_argument("--category", help="分类，如 交通 / 音乐")
    li.add_argument("--search", help="关键词")
    li.add_argument("--limit", type=int, default=30)
    li.add_argument("--only-ok", action="store_true", help="只列上次检测连通的")
    li.set_defaults(func=cmd_list)

    pg = sub.add_parser("page", help="生成播放页")
    pg.add_argument("--province")
    pg.add_argument("--category")
    pg.add_argument("--search")
    pg.add_argument("--limit", type=int, default=0, help="最多收录多少个，0=不限")
    pg.add_argument("--only-ok", action="store_true")
    pg.add_argument("--out", help="输出 HTML 路径")
    pg.add_argument("--title", help="页面标题")
    pg.set_defaults(func=cmd_page)

    args = ap.parse_args()
    raise SystemExit(args.func(args) or 0)


if __name__ == "__main__":
    main()
