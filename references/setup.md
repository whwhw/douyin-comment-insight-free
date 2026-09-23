# 安装和配置

交付物为 Codex Skill 与 Python 脚本。分析由运行 Skill 的 Codex 完成，脚本负责采集、转写、校验；无需另配大模型 API。

## 安装

需要 Python 3.10+。在解压后的技能目录执行（Windows 可将 python3 换为 py -3）：

```sh
python3 install.py
```

进入安装器输出的目录，创建独立环境并安装依赖：

```sh
python3 -m venv .venv
# macOS/Linux
.venv/bin/python -m pip install -r requirements.txt
# Windows
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

后续示例中的 python 使用此虚拟环境解释器。用户只在本地编辑 `.env`，不要在聊天中粘贴密钥。环境变量优先于 `.env`；空值或 replace_ 占位不视为有效配置。

在线分析配置 `TIKHUB_API_KEY` 和 `TIKHUB_BASE_URL`。本地媒体提取不需要 TikHub。评论数量是接口实际返回值，不能将请求上限当成获取量。

## 本地文案提取

FFmpeg 负责音频提取，whisper.cpp 负责语音识别，两者都需安装。

- FFmpeg 官方下载：https://ffmpeg.org/download.html 。确保 ffmpeg 和 ffprobe 在 PATH，或配置 FFMPEG_PATH、FFPROBE_PATH 为可执行文件的绝对路径。
- whisper.cpp 官方安装/构建与模型说明：https://github.com/ggml-org/whisper.cpp 。Windows 使用官方对应平台构建或按官方说明编译，macOS 同样使用官方说明。
- 中文请使用多语言模型，例如 small，不使用 small.en。通过项目自带 models/download-ggml-model.sh 或 Windows 对应脚本获取模型，配置 WHISPER_MODEL_PATH；模型不随技能包分发，下载占用数百 MB 以上，具体大小以所选模型为准。
- WHISPER_CLI_PATH 可指定 whisper-cli 可执行文件。路径包含空格时在 `.env` 中用双引号包裹。

```sh
python scripts/doctor.py --mode collect
python scripts/doctor.py --mode local
python scripts/transcribe_works.py --media "/absolute/path/video.mp4" --provider local --output-dir "/absolute/path/output"
```

输出 spoken/*.txt、subtitles/*.srt、asr/*.json 和 transcription-manifest.json。出现 needs_review 时仍可查看原文，请人工核对识别内容。时间完整性不保证逐字准确，重复识别、缺失片段要人工复核。

## 更新技能

从新下载的包执行 `python install.py --upgrade`。安装器备份旧版本并保留 `.env`、`.venv` 与 workspace。

## 故障处理

- doctor 只报告配置是否存在，不联网、不验证额度或密钥有效性。
- 采集失败按输出中的 --resume 命令继续同一次运行；已成功响应复用，不覆盖旧报告。需要全新数据时不带 --resume。
- 转写重复运行同一 --input，复用同账号、同作品、同服务、时长一致且通过质量检查的 manifest，不必等报告发布。需要重转时显式 --force-transcribe。
- Windows 尚需在真实 Windows 环境完成验收；本包使用跨平台路径和子进程接口，不以静态检查替代实机测试。
