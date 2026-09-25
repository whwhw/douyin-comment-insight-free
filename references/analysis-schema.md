# 分析输出约定

`findings.json` 只写 Codex 基于真实评论完成的语义归纳，至少包含：

```json
{
  "lane": "账号内容赛道",
  "summary": "一句话结论",
  "metrics": {
    "comments": 0,
    "highValueSignals": 0,
    "needClusters": 0,
    "highPotential": 0
  },
  "viewpoints": [],
  "run": {
    "status": "completed",
    "completedAt": "ISO-8601 时间"
  }
}
```

每个观点对象包含 `id`、`title`、`summary`、`evidenceCommentIds`。

规则：

- 证据 ID 必须存在于 `analysis-input.json` 的 `comments[].commentId`。
- 没有证据支持的判断写“待验证”，不得虚构付费意愿。
- 不改写原始评论文本，不在输出中保存 API Key。

`finalize_analysis.py` 会把观点 ID 回填到评论，并拒绝不存在的证据 ID。

## 对标作品洞察

`work-findings.json` 需包含 `qualifiedWorkIds`、`workAnalyses`、`recreationAngles` 和 `coverage`。

- 作品分析必须记录 `referenceId`、`sourceKind`、`transcriptComplete`、`spokenScriptPath`、`asrMetadataPath`、`sourceTopic`、`targetAudienceProblem`、`coreTension`、`openingHook`、`structureBeats`、`proofSequence`、`retentionDevice`、`cta`、`goldenQuotes`、`transformableVariables` 和 `prohibitedCopyElements`。
- `transcriptSections` 中每个真实口播分段除 `time/startMs/endMs/structure/text` 外，应补充 `review`，包含 `strength`、`risk`、`improvement`。点评必须说明该段结构的作用、潜在问题和可执行优化，不得把结构写成播放结果的因果结论；证据不足时使用“可能”“需验证”。
- `sourceKind` 只有 `full_asr` 或 `platform_subtitle` 可进入内容分析。金句必须存在于对应口播文本。
- 二创角度必须记录 `referenceIds`、`derivationType`、`motherTopic`、`preservedElements`、`changedElements`、`newProofPlan` 和 `proofRequirement`。
- 允许的派生类型为 `new_example_same_mechanism`、`new_scene_same_problem`、`new_format_same_argument`、`comparison_with_new_proof` 和 `cross_source_synthesis`。
- 单条母作品最多支持两个直接二创角度；跨作品综合至少引用两条合格作品。

## 输出校验约定

findings 不得覆盖 accountId/profile/works/comments/source/selectedWorks/workWindow/updatedAt/followers/displayName。原始文本始终从 analysis-input 读取。可写 summary、lane、overviewHeadline、overviewDescription、viewpoints、keywords、limitations、run 等分析字段。没有评论时 viewpoints 为空。

structureBeats 使用字符串数组或 `{ "label": "结构名", "summary": "作用", "startMs": 0, "endMs": 1000 }`。transcriptSections 是以作品 ID 为键的字典，分段时间必须等于连续ASR片段边界；原文拼接完整覆盖ASR。readingText 仅补标点/空格，review 三项全部必填。金句同样按完整连续片段引用，记录 text/startMs/endMs/type/whyItWorks/reusablePattern。

manifest 的 needs_review/failed 作品不进入 qualifiedWorkIds；完成作品的路径从 manifest 原样传入。报告中通过 limitations 明示部分转写、评论采集失败、旧作混入和识别误差，不用零替代缺失的播放/收入数据。
