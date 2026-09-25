# 高速文案提取

商品功能名称使用“高速文案提取”。实际语音识别由用户自己的火山引擎服务提供；不隐藏供应商，不承诺秒出或固定倍速。本机仍需 FFmpeg/FFprobe 提取并核验音频。运行费用由用户承担，价格和服务限制以供应商控制台为准。

在 .env 设置：

```dotenv
ASR_PROVIDER=cloud
VOLCENGINE_SPEECH_API_KEY=replace_with_your_key
```

也支持旧版凭据 VOLCENGINE_SPEECH_APP_ID + VOLCENGINE_SPEECH_ACCESS_TOKEN。新式 Key 优先；不混合两套请求头。两套都未配置时停止高速提取并指导配置，不能自动换成本地。使用 `--provider local` 或配置 ASR_PROVIDER=local 可明确选择本地。

官方 API：https://www.volcengine.com/docs/6561/1631584?lang=zh
端点：POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash
资源 ID：volc.bigasr.auc_turbo

云端请求有明确超时，不对可能已计费的请求自动重试。网络失败或额度不足保留其他已完成作品，人工确认后重跑失败项。缓存复用同账号、作品、服务及一致时长的合格转写，不将本地缓存冒充云端结果。
