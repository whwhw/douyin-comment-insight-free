# 抖音账号洞察 Skill · 免费版

> 使用前必读：本包不是解压即用的软件。请先安装 Python 依赖、音频工具，并在安装目录的 `.env` 中配置自己的服务凭据。分析由 Codex 按 SKILL.md 执行，脚本本身不会独立调用大模型生成分析。

> 已实测：macOS 下的小规模采集、本地转写、字幕输出、安装与升级。Windows 尚未实机验收。


版本：1.0.0  
技能名称：`douyin-comment-insight-free`  
安装包：`douyin-comment-insight-free-1.0.0.zip`

## 教学与联系

使用教程请查看：[教学使用文档](https://tyzwvof1d8.feishu.cn/wiki/BxaYwKTmUiIV0Ikud8LcVfx8nKh)。

如果有任何问题，可以联系微信：`ai_coder_wang`。

## 推荐搭配使用

推荐搭配之前分享的「运营助手」一起使用：先用本技能了解账号表现、整理评论讨论点和提取口播原文，再把分析结果交给运营助手，作为后续选题与内容运营的参考。

## 它能帮你做什么

输入一个抖音号，了解这个账号在做什么内容、哪些作品相对表现更好，以及观众在评论区讨论什么。还可以用本地模型把视频口播转成文字和字幕，方便阅读与整理。

适合已经会使用 Codex，希望先体验账号分析、评论归纳和文案提取的创作者。交付形式是 Skill 技能包和脚本，需要在自己的电脑上安装和运行。

## 包含的功能

| 功能 | 交付内容 |
|---|---|
| 账号概况 | 昵称、简介、粉丝数及本次观察范围 |
| 作品表现 | 点赞、评论、收藏、分享等接口实际返回的数据 |
| 高表现作品排名 | 当前账号观察样本内的相对排名 |
| 评论整理 | 原始评论、高赞评论及主要讨论点 |
| 基础账号诊断 | 对话内简评，结论关联评论原文证据 |
| 本地文案提取 | 使用 FFmpeg 提取音频，使用 whisper.cpp 转写 |
| 原文和字幕导出 | TXT 原文、带时间戳的 SRT 字幕 |
| 历史数据复用 | 已通过检查的转写可复用，采集失败可按提示续跑 |

默认最多观察 30 条作品、每条最多请求 100 条评论；实际数量以接口返回为准。默认为选中的最多 5 条代表作品提取口播，不是转写全部 30 条。


## 安装前需要准备

- Codex 及其运行本地脚本的环境。
- Python 3.10 或更高版本。
- 在线分析账号时，需要自己的 TikHub API Key。
- 本地转写时，需要 FFmpeg、FFprobe、whisper.cpp 和多语言识别模型。

FFmpeg 只负责音频处理，语音转文字由 whisper.cpp 完成。模型需要单独下载，不包含在技能包内。中文转写应使用多语言模型，例如 small，不使用仅支持英文的 small.en。

## 安装步骤

### 1. 安装技能

解压安装包，在解压目录执行：

```sh
python3 install.py
```

Windows 可将 `python3` 换为 `py -3`。安装器默认安装到用户目录下的 `.codex/skills/douyin-comment-insight-free`，并显示实际路径。

### 2. 安装 Python 依赖

进入安装器输出的技能目录。

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

### 3. 填写本地配置

编辑安装目录中的 `.env`，填写自己的配置。不要把真实密钥发送到聊天或放进公开文件。

```dotenv
TIKHUB_API_KEY=填写自己的采集服务密钥
TIKHUB_BASE_URL=https://api.tikhub.dev
ASR_PROVIDER=local
WHISPER_MODEL_PATH="填写本地多语言模型的绝对路径"
ASR_LANGUAGE=zh
```

如果相关程序不在 PATH 中，再填写：

```dotenv
FFMPEG_PATH="ffmpeg可执行文件的绝对路径"
FFPROBE_PATH="ffprobe可执行文件的绝对路径"
WHISPER_CLI_PATH="whisper-cli可执行文件的绝对路径"
```

安装工具和模型的具体指引见包内 `references/setup.md`。仅处理本地视频时，不需要 TikHub Key。

### 4. 检查配置

以下 `python` 均指刚创建的虚拟环境解释器：macOS 使用 `.venv/bin/python`，Windows 使用 `.venv\Scripts\python.exe`。

```sh
python scripts/doctor.py --mode collect
python scripts/doctor.py --mode local
```

自检只检查配置和依赖是否存在，不代表密钥、余额或在线服务一定可用。

## 怎么使用

在 Codex 中明确点名技能：

```text
使用 $douyin-comment-insight-free 分析抖音号 xxx，给我账号简评和评论主要讨论点，并提取代表作品的原文和字幕。
```

只提取本地视频：

```text
使用 $douyin-comment-insight-free，提取这个本地视频的完整口播，导出 TXT 和 SRT。
```

复用已有数据：

```text
使用 $douyin-comment-insight-free，复用历史数据分析 xxx，不重新采集。
```

账号昵称存在歧义时，需要提供真实抖音号或可核验的主页信息。不要将视频 ID 当作抖音号。

## 结果保存在哪里

默认保存在安装目录的 `workspace` 中，每次采集有独立运行目录。Skill 会返回本次结果的实际路径。

- `analysis.json`：基础分析数据。
- `evidence/spoken/*.txt`：原始转写文本。
- `evidence/subtitles/*.srt`：字幕文件。
- `evidence/transcription-manifest.json`：转写状态与文件位置。

基础简评会直接在对话中交付。可以通过 `.env` 中的 `DOUYIN_INSIGHT_WORKSPACE` 指定其他数据目录。

## 结果说明


作品排名只代表本次账号样本内的相对表现，不能视为平台级爆款榜单。评论记录不等于独立观众人数，讨论或购买意向不等于成交。

转写可能出现错字。检测到时间缺失、截断或重复识别时，会标记待复核；生成字幕不代表文字已人工精校。

## 更新技能

从新下载的免费版安装包执行：

```sh
python3 install.py --upgrade
```

更新会保留 `.env`、虚拟环境和工作数据，并备份旧安装目录。

## 当前测试情况

免费版 11 项适用自动化测试通过，已完成真实小规模账号采集、本地中文转写、TXT/SRT 导出和转写复用测试。macOS 安装与升级已经验证；Windows 实机兼容性仍待验收。

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
