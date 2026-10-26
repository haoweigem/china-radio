---
name: china-radio
description: "全国广播电台收听。覆盖中央台（央广 CNR / 国际台 CRI / CGTN）与 31 个省级行政区共 1100+ 个电台，可按省份、分类（新闻/交通/音乐/文艺/经济/民族等）或关键词查找，并生成可点开即听的网页播放器。当用户想听国内广播、听某省/某市的电台、听新闻广播或交通台，或问「有哪些中文电台」时使用。"
---

# 全国广播电台（china-radio）

1188 个国内电台，覆盖中央台 + 31 个省级行政区 + 港澳。离线数据集，打开就能用，
不需要账号、不需要 API key。

## 生成播放页（主要用法）

```bash
python -X utf8 "<skill>/scripts/radio.py" page --out "<cwd>\radio.html"
```

常用筛选组合：

| 需求 | 参数 |
|---|---|
| 某个省 | `--province 广东`（省份名用规范简称：内蒙古、黑龙江、中国香港） |
| 某类电台 | `--category 交通` / `音乐` / `新闻` / `文艺` / `经济` / `民族` |
| 关键词 | `--search 哈尔滨` / `--search 戏曲` |
| 只要连通的 | `--only-ok` |
| 限制数量 | `--limit 40` |

生成后把 HTML 用 present_files 打开，用户点卡片即可收听。HLS 流由页面内置的
hls.js 解码，不依赖外网 CDN（已内联进 HTML）。

## 查询（不开页面也能看）

```bash
python -X utf8 radio.py stats                      # 总量 + 分类/省份分布 + 连通率
python -X utf8 radio.py provinces                  # 各省电台数
python -X utf8 radio.py categories                 # 各分类数量
python -X utf8 radio.py list --province 四川 --category 新闻
python -X utf8 radio.py list --search 相声 --limit 10
```

## 更新数据

```bash
python -X utf8 build_data.py --check     # 重新抓取 + 全量连通检测（约 1 分钟）
```

数据来源是公开的 m3u 聚合列表，构建脚本负责清洗名称、识别省份、去重、筛选国内台。
地名映射在 `scripts/regions.py`，遇到归错省的情况在那里补一条即可。

## 已知情况

- **连通率约 78%**：927/1188 在当前网络下可连。数据里已记录 `ok` 标记，
  页面会标注「上次检测未连通」，并默认排到最后。
- **HLS 占多数**：668 个是 m3u8 流，浏览器需要 hls.js（页面已内置）。
- 部分央广/CRI 官方源对非浏览器 UA 返回 403，实际在浏览器里能播，
  这类会被检测误判为未连通。
- 数据里的 `alt` 字段存了备用源（同一电台的另一条流），当前页面只用主源。
- 版权归各电台所有，本工具只做公共广播流的聚合索引，不存储音频。

## 排错

点了没声音 → 换一个台（约两成源会失效，属正常）。整页都没声 → 检查是否
点到「上次检测未连通」的台，或该网络环境屏蔽了流媒体端口。
