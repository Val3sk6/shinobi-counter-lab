# 案例数据结构

每条案例记录在 `data/cases.json` 中。

| 字段 | 含义 |
| --- | --- |
| id | 唯一标识 |
| def / atk | 防守和进攻的三个站位，顺序严格对应 |
| grade | primary 原帖 / repost 转载 |
| review | ready 可检索 / hold 待核验 / archive 历史归档 |
| url / source | 公开证据链接、来源平台 |
| version / date | 游戏版本与发布日期 |
| note / condition | 机制、适用条件与异常 |
| lim / spanBasis | 作者提及的跨度、百分比分母 |
| validation / evidence | 核验程度与证据类型 |

`def` 的每个位置可为固定忍者名、允许名单，或来源明确声明无要求时的 `null`。不应将未测试的站位写成任意。

跨度有两种算法：`(敌方-我方)/我方` 和 `(敌方-我方)/敌方`；原作者未注明口径时必须使用 `spanBasis=unspecified`。

已有破阵案例匹配数不代表真实胜率；请勿发布无证据的“必胜”结论。仅保存自己的简明结构化摘要，不搬运未获授权的完整视频、图片和攻略文案。
