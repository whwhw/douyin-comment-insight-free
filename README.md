# 抖音账号洞察 Skill · 免费版

> 使用前必读：本包不是解压即用的软件。请先安装 Python 依赖、音频工具，并在安装目录的 `.env` 中配置自己的服务凭据。分析由 Codex 按 SKILL.md 执行，脚本本身不会独立调用大模型生成分析。



版本：1.1.0
技能名称：`douyin-comment-insight-free`  
安装包：`douyin-comment-insight-free-1.1.0.zip`

## 教学与联系

使用教程请查看：[教学使用文档](https://tyzwvof1d8.feishu.cn/wiki/BxaYwKTmUiIV0Ikud8LcVfx8nKh)。

如果有任何问题，可以联系微信：`ai_coder_wang`。

## 推荐搭配使用

推荐搭配之前分享的「运营助手」一起使用：先用本技能了解账号表现、整理评论讨论点和提取口播原文，再把分析结果交给运营助手，作为后续选题与内容运营的参考。

## 它能帮你做什么

输入一个对标抖音号，把作品表现、完整口播和评论需求放在一起分析，得到有来源依据的结构拆解、逐段点评和二创方案，并保存为可查看、可导出的报告。

适合已经会使用 Codex，需要持续研究对标账号、积累内容案例和规划下一条作品的创作者。交付形式是 Skill 技能包和脚本，在自己的电脑上运行，数据默认保存在本地。

## 包含的功能

| 功能 | 交付内容 |
|---|---|
| 账号与作品观察 | 账号概况、互动数据、样本内高表现作品排名 |
| 评论需求分析 | 讨论焦点、需求归纳与评论原文证据 |
| 高速文案提取 | 使用用户配置的云端语音服务完成口播转写 |
| 本地文案提取 | 可显式切换到本地 FFmpeg + whisper.cpp |
| 原文与字幕导出 | TXT 原文、带时间戳的 SRT 字幕 |
| 口播结构拆解 | 目标问题、核心冲突、段落安排、证据顺序、留存机制与行动引导 |
| 金句筛选 | 完整原文、真实时间范围、表达作用和可借鉴句式 |
| 逐段点评 | 每段的优点、风险和具体改进建议 |
| 二创方案 | 来源作品、保留机制、可改变量、开场、拍摄步骤和补证方案 |
| 报告与洞察库 | HTML 详情页、账号索引、历史查看与更新 |
| 报告导出 | 仅包含当前账号及必要资源的 ZIP 报告包 |

默认最多观察 30 条作品、每条最多请求 100 条评论，实际数量以返回结果为准；默认提取最多 5 条代表作品的完整口播。深度分析只使用通过证据检查的完整转写，数量不足时如实说明。

## 安装前需要准备

- Codex 及本地脚本运行环境。
- Python 3.10 或更高版本。
- TikHub API Key，用于在线账号采集。
- FFmpeg 和 FFprobe，用于音频提取与时长检查。
- 火山引擎语音服务凭据，用于高速文案提取。
- 如需本地模式，另安装 whisper.cpp 和多语言模型。

无需另外配置分析用的大模型 API：分析由当前运行 Skill 的 Codex 完成。工具安装说明见包内 `references/setup.md`。

## 安装步骤

### 1. 安装技能

在免费版解压目录执行：

```sh
python3 install.py
```

Windows 可使用 `py -3`。默认安装到用户目录下的 `.codex/skills/douyin-comment-insight-free`，实际路径以安装器输出为准。

### 2. 安装 Python 依赖

进入安装后的免费版技能目录。

macOS / Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows：

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. 配置高速提取

在安装目录的 `.env` 中填写自己的凭据：

```dotenv
TIKHUB_API_KEY=填写自己的采集服务密钥
TIKHUB_BASE_URL=https://api.tikhub.dev
ASR_PROVIDER=cloud
VOLCENGINE_SPEECH_API_KEY=填写自己的火山语音服务密钥
ASR_LANGUAGE=zh
```

也支持旧版凭据组合：

```dotenv
VOLCENGINE_SPEECH_APP_ID=填写自己的APP_ID
VOLCENGINE_SPEECH_ACCESS_TOKEN=填写自己的ACCESS_TOKEN
```

新式 API Key 与旧版组合选择一套即可；同时存在时新式 Key 优先。不要把密钥写进报告、截图或聊天。

如果 FFmpeg/FFprobe 不在 PATH 中，填写 `FFMPEG_PATH` 和 `FFPROBE_PATH` 的绝对路径。

### 4. 检查配置

以下 `python` 指虚拟环境解释器：macOS 为 `.venv/bin/python`，Windows 为 `.venv\Scripts\python.exe`。

```sh
python scripts/doctor.py --mode collect
python scripts/doctor.py --mode cloud
```

自检只检查配置与依赖是否存在，不代表密钥有效或余额充足。高速提取的详细接入说明见 `references/high-speed.md`。

### 5. 可选：使用本地转写

安装 whisper.cpp 和多语言模型后，在 `.env` 设置：

```dotenv
ASR_PROVIDER=local
WHISPER_MODEL_PATH="模型文件的绝对路径"
WHISPER_CLI_PATH="whisper-cli可执行文件的绝对路径"
```

若 whisper-cli 已在 PATH 中，可省略 WHISPER_CLI_PATH。中文使用多语言模型，不使用英文专用模型。再执行：

```sh
python scripts/doctor.py --mode local
```

服务失败时不会静默从云端切成本地。可以修复凭据、网络或额度后续跑，也可以明确选择本地模式。

## 怎么使用

完整分析一个账号：

```text
使用 $douyin-comment-insight-free 分析抖音号 xxx，完成评论需求、口播结构、金句、逐段点评和二创方案，并导出完整报告。
```

明确使用高速提取：

```text
使用 $douyin-comment-insight-free，用高速文案提取分析 xxx。复用已有合格口播，只处理缺失的部分。
```

明确使用本地提取：

```text
使用 $douyin-comment-insight-free，这次使用本地转写分析 xxx。
```

仅查看已有报告：

```text
使用 $douyin-comment-insight-free，查看 xxx 的历史报告，不重新采集。
```

只基于已有数据继续分析：

```text
使用 $douyin-comment-insight-free，复用历史数据重新分析 xxx，不调用采集和云端转写。
```

需要结合自己的账号给出建议时，补充定位、目标观众、可用素材和拍摄条件；没有这些信息时，二创方案仅为基于对标内容的待验证方向。

## 报告与数据保存

默认数据保存在技能目录的 `workspace`。可以通过 `.env` 的 `DOUYIN_INSIGHT_WORKSPACE` 指定其他目录。

- `workspace/runs/`：每次采集、分析与转写证据。
- `workspace/site/comment-insight-index.html`：洞察库首页。
- `workspace/site/<抖音号>.html`：对应账号详情页。
- `evidence/spoken/*.txt`：口播原文。
- `evidence/subtitles/*.srt`：字幕文件。

Skill 会返回实际文件路径。报告 ZIP 解压后打开 `index.html`。导出时只包含当前账号，不附带其他账号的报告；同时去除本机证据文件路径。原始评论仍属于报告内容，分享前需自行检查。部分远程封面和图标动效依赖网络，主体分析数据已经嵌入页面。

## 分析质量说明

分析结论需关联真实评论或转写证据。排名仅表示观察样本内表现，不保证播放、涨粉、收益或成交。购买意向不能替代订单证据，原作者的产品能力或收入陈述不等于已独立核实。

转写完整性校验不等于逐字准确。发现重复识别、截断或异常时间戳时，原文保留并标记待复核，不继续据此生成结构点评或二创。部分作品失败时，可以交付其他已完成模块，并明确缺口。

## 更新技能

在新下载的安装包中执行 `python3 install.py --upgrade`。安装器会备份旧版本，并保留配置、虚拟环境和工作数据。

## 当前测试情况

已通过安装更新、采集身份核验、转写证据校验、HTML 发布和单账号报告导出的自动化测试。浏览器验收覆盖桌面与 390px 窄屏、详情弹窗、评论证据、空数据和报告导出后的打开流程。

本地中文转写与小规模在线采集已在 macOS 测试。云端接口已做模拟测试，真实服务的识别效果、速度与计费，以及 Windows 实机仍待验证。

## 包内文件导航

- `SKILL.md`：给 Codex 读取的工作流程与证据规则。
- `install.py`：安装和更新。
- `.env.example`：配置模板；安装后自动生成 `.env`。
- `requirements.txt`：Python 依赖。
- `scripts/doctor.py`：配置与依赖检查，不验证在线额度。
- `scripts/workflow.py`：历史检查、采集准备和续跑。
- `references/setup.md`：工具、模型和故障处理说明。
- `examples/`：虚构离线样例，不是真实账号分析。
- `package-manifest.json`：交付文件校验清单。

如果只复制 SKILL.md 而没有脚本及配套资源，不能完成本包的功能。
