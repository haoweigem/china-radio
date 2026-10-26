# 全国广播电台

一个可以直接用浏览器收听的全国广播电台合集：**1188 个电台，覆盖中央台与 31 个省级行政区**，
按省份、类型、关键词筛选，点一下就能听。附带一个构建脚本，可以随时刷新台单。

不依赖任何商业音乐平台，收的是各地广播电台的公开直播流，无需账号、无需 API key。

## 特点

- **覆盖全**：央广 CNR 全系列、国际台 CRI、CGTN 多语种，以及 31 个省级行政区
  到地市/区县的电台，另有港澳台。
- **能分类**：自动识别新闻、交通、音乐、文艺、经济、生活、综合、农村、民族语言等标签。
- **能筛选**：省份下拉 + 分类标签 + 搜索框，三者可以叠加。
- **HLS 免依赖**：网页播放器内置 hls.js，HLS 流不依赖外网 CDN，离线也能用。
- **自带体检**：构建时对全部流做并发连通检测，结果写进数据，失效的台标记出来并排到最后。

## 数据

| 项目 | 数值 |
|---|---|
| 电台总数 | 1188 |
| 省级行政区 | 31 + 港澳台 |
| 流格式 | HLS(m3u8) 668 · MP3 554 · 其他 6 |
| 连通率 | 927 / 1188（约 78%） |

分类分布：综合 259、交通 227、新闻 185、音乐 112、生活 66、文艺 52、经济 43、
民族语言 23、农村 16、外语 12、体育 4。

省份 Top 6：江苏 82、浙江 79、广东 79、山东 78、河南 65、湖南 60。

## 快速开始

```bash
git clone https://github.com/haoweigem/china-radio.git
cd china-radio

# 生成全部电台的播放页
python -X utf8 scripts/radio.py page --out radio.html

# 只看广东的交通台
python -X utf8 scripts/radio.py page --province 广东 --category 交通 --only-ok --out gd.html
```

打开生成的 HTML，点任意卡片即可收听。

## 命令行

```bash
python -X utf8 scripts/radio.py stats            # 总量、分布、连通率
python -X utf8 scripts/radio.py provinces        # 各省电台数
python -X utf8 scripts/radio.py categories       # 各类型数量
python -X utf8 scripts/radio.py list --province 四川 --category 新闻
python -X utf8 scripts/radio.py list --search 相声
python -X utf8 scripts/radio.py page --search 戏曲 --out xiqu.html
```

参数说明：

- `--province` 省级名称，用规范简称：`内蒙古` `黑龙江` `中国香港`
- `--category` 分类名：`新闻` `交通` `音乐` `文艺` `经济` `生活` `综合` `农村` `民族` `外语` `体育`
- `--search` 关键词，匹配台名与省份
- `--only-ok` 只收录上次检测连通的电台
- `--limit` 限制收录数量，0 为不限

## 更新数据

```bash
python -X utf8 scripts/build_data.py --check
```

约 1 分钟。流程是：抓取公开 m3u 聚合列表 → 清洗名称 → 识别省份与类型 → 去重 →
并发检测连通性 → 写入 `data/stations.json`。

遇到电台归错省份，在 `scripts/regions.py` 的 `CITY_TO_PROVINCE` 里补一条地名映射即可。

## 项目结构

```
china-radio/
├── SKILL.md                     # Agent Skill 说明（可直接放进 skills 目录使用）
├── data/
│   └── stations.json            # 清洗后的电台数据集
├── scripts/
│   ├── build_data.py            # 抓取 + 清洗 + 检测
│   ├── regions.py               # 地名到省份的映射表
│   └── radio.py                 # 查询 + 生成播放页
└── assets/
    ├── player_template.html     # 播放页模板
    └── hls.min.js               # HLS 解码（构建时内联进页面）
```

也可以作为 Agent Skill 使用：把整个目录放进 `~/.workbuddy/skills/china-radio/`，
之后对 Agent 说「听会儿广东的交通台」即可。

## 说明

- **连通率约 78%** 属于正常范围。广播流的可用性会随时间变化，两成左右的源会失效，
  重新跑一次 `build_data.py --check` 即可刷新状态。
- 部分央广、CRI 的官方源会对非浏览器 User-Agent 返回 403，检测时会被判为不可用，
  但在浏览器里实际能播。
- 本项目的音频全部指向各电台的**公开直播流**，仓库不存储、不转码、不分发任何音频内容，
  只做地址索引。版权归各电台所有，请遵守当地法律法规与电台的使用条款。
- 数据来源于公开的 m3u 聚合列表，本项目对其进行清洗与结构化整理。

## License

MIT
