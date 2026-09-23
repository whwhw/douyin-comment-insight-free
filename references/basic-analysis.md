# 基础简评契约

findings.json 示例（证据 ID 必须替换为本次实际评论，不复制示例当真实结论）：

```json
{
  "lane": "由作品和简介归纳的内容赛道",
  "summary": "有证据支持的账号简评",
  "viewpoints": [{"id":"v1","title":"具体讨论点","summary":"基于评论的归纳，说明适用样本","evidenceCommentIds":["真实评论ID"]}],
  "limitations": ["观察窗口、评论缺失和数据时间限制"]
}
```

没有评论时 viewpoints 为空，简评解释仅有作品数据。输出账号简评和有原文证据的评论讨论点。brief.py 拒绝越界字段和不存在的证据，不覆盖原始作品/评论。
