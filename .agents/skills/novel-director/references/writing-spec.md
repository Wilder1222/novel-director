# 章、剧情、描写与铺垫的硬规格

按[自述、练习与晋升铺垫](interiority-progression.md)规划有关章节：在章卡明确关键自省、具体尝试/反馈/调整、晋升前证/门槛与前后差异，用已有detail_requirements和setups登记过程/铺垫；重复稳定过程可概述，不强制每章修炼或突破，未知设定保持候选。人物/成稿只拿当前可知或可展示的材料，未来回收答案不下发。

适用于新draft/revise任务。主会话把自然语言章卡整理为书内`writing_spec.json`，不让作者填表。
同时按[小说对白密度](dialogue-density.md)核交流段、场景和整章的展开/概述、变化承接与时空/身体条件。密度不按比例/句数判，合理连答可保留；问题不能用无关旁白或逐句动作稀释，也不授权成稿删改已采纳对白。
dialogue_context还要结合当场安全对照核人物关系、当前任务、性格、常态/当场语气与条件口头禅，未使用口头禅不判错，不把单向关系或性格标签当强制对白模板；人物私密speech_style不自动转发审稿。
dialogue_embodiment延续对白与行为联合审查：省略号、骤断、结巴、重复和改口按语境选择，既审过平也审机械堆叠；保留已采纳speech原始符号、次数与顺序，不设配额，详[联合创作](dialogue-embodiment.md)。
先用[参考库](reference-library.md)看本书适用的采集/阅读范围，不能把别书章长当统一定律。
作者当前明确要求每章3000–6000 LN，闭区间含上下限；新章计划必须采用此硬范围，除作者后续明确调整，不由主会话按题材擅自放宽。剧情默认仍500–2500 LN。
动态与静态新项目模板同步该章范围，模板origin仍为tool_default；本书依据本次原话保存author_request，不代表其他作者已确认，也不自动生成具体章卡。
旧研究中的2500–4000覆盖统计保留旧口径；《我有一座冒险屋》1/50、《剑来》28/50仅对应旧区间，不是3000–6000的新统计。当前数值来自作者要求，不称普适最优。
冻结后不能成稿才暗放宽。改规格会使既有Run/排练/阶段失效，需要显式新建与重新核验。

## 计数、粒度和实际产物

- LN逐Unicode码点统计L/N分类（含中文、拉丁字母和数字）；空白、标点、符号、组合标记不计。不规范化正文；记录实际Unicode版本。**不是平台计费/福利/日更口径**。
- 章、完整剧情片段、场景、节拍不同：短结算/动作/转场归入其剧情，不各套500下限。跨章剧情弧仍用story_units，不能把一章片段当全弧验收。
- 每章明确range；每plot明确purpose/range，下面parts各有scene_id/order/purpose/range。剧情可以跨场，场可含多个剧情；part只归一个剧情/场，顺序与已登记场景相符。同一场景回返须另建实例。
- 计划先核父子预算及场景容量是否共同可行；成稿再重算章、剧情、部件。不能用总章字数掩盖单剧情超限。标题、附言、日志另存，不能计入正文凑数；格式识别不能穷尽隐含污染，仍需语义审查。
- 单段人物/动作/环境描写若需要独立硬字数，就规划具名part和范围；不按人物人数机械分配外貌、心理、五感配额。

主会话准备的结构示意（仅schema示意，所有ID/任务/上下限须来自当前章卡）：

```json
{
  "schema_version":"1", "counter":"letters_numbers_v1", "origin":"tool_default",
  "defaults":{"chapter_range":{"min":3000,"max":6000},"plot_range":{"min":500,"max":2500}},
  "chapters":[{
    "chapter_id":"V01-C01", "range":{"min":3000,"max":6000},
    "plot_units":[
      {"id":"P1","purpose":"登记出现差异，人物决定核对来源","range":{"min":1000,"max":2000},
       "parts":[{"id":"A","scene_id":"one","order":1,"purpose":"展开核对过程与选择代价","range":{"min":1000,"max":2000}}]},
      {"id":"P2","purpose":"对质差异并尝试改变局面","range":{"min":1000,"max":2000},
       "parts":[{"id":"B","scene_id":"two","order":2,"purpose":"展开回应与阻碍","range":{"min":1000,"max":2000}}]},
      {"id":"P3","purpose":"承担后果并形成下一步选择","range":{"min":1000,"max":2000},
       "parts":[{"id":"C","scene_id":"three","order":3,"purpose":"展开结算和关系余波","range":{"min":1000,"max":2000}}]}
    ],
    "detail_requirements":[{"id":"D1","scope":"P1","criterion":"差异能从当前可见材料复原；不替另一人物猜定动机"}],
    "setups":[], "setup_strategy":"承接已出现的疑问，当前不新增未经计划的长线伏笔。"
  }]
}
```

## 不让写手手算哈希或偏移

推荐compose返回`{"request_id":"实际当前ID","parts":[{"part_id":"A","text":"实际完整原文"}]}`，
工具按计划顺序逐字拼接，不自动插入分隔符，确定性建立SHA与偏移。所需换行写在part.text里。
可同时给text，但必须逐字一致；parts与精确content_map二选一。单part的text可确定性归属全文。
多part也可给text与内容map，不能猜边界。CLI sidecar支持`{"parts":[...]}`，拼接须等于实际候选。

映射最终形状：schema_version/spec_sha256/counter/unicode_version/chapter_id/candidate_sha256/segments；
每segment为part_id/start/end，偏移按Unicode码点，不是字节/JS UTF16。必须全覆盖、无重叠/漏尾/倒排。
组章原文原序可平移旧map；重写sections可给完整parts，须与sections+转场的整章逐字相等；
section不得计入另一场景。默认转场归前场最后part并计数，不能遗漏。保持已采纳对白、场序和POV。
定向修订同part局部补丁可重映射；跨part须新显式map/parts。预检失败不能留下已应用patch/候选。

## 人物、事情、描写、情感与铺垫的语义门槛

每章额外必审dialogue_context与dialogue_embodiment：逐位发言者核人设/场景/剧情/情绪/关系与措辞、语气词、表情/动作是否共同成立；当前可见裁定事件由主会话安全附给审查者。允许正式/紧急短答、沉默、无对白及有依据的反差，不按句配额，详[联合创作](dialogue-embodiment.md)。漏审或uncertain不能过检。

每章必审：重要人物当时目标/所知/阻碍/选择依据/代价；辨识细节是否服务处境；
POV观察与推断；感官细节的实际作用；情感触发—理解—回应—余波；解释/重复是否增加作用；铺垫承接策略。
每剧情必审：触发—行动—阻碍/调整—结果—承接与关键过程/位置/物件可复原性。
安静观察、沉默、氛围与节奏也可以承担作用，不要求每段反转；关系不默认爱情。

detail_requirements可按chapter或plot ID增加具体要求。setups每项含id/scope/criterion/operation/prior，
operation是plant/reinforce/payoff，回收completion为partial/full：
plant核当前首次呈现，不虚构前章证据；reinforce/payoff须真实先前证据，强化必须增量，回收须产生作用/重释。
prior引用`manuscript/此前章.md`或`candidate`确切引文及可选start/end/sha256；同章前证必须早于作用证据。
读者看过不等于人物知道。只给当前场安全要求，不能把未来真相或整个私密铺垫表交角色。

Run报告额外含`writing_spec_review:{spec_sha256,candidate_sha256,checks:[{id,verdict,rationale,citations}]}`，
需完整覆盖spec-budget所列targets，verdict为satisfied/partial/missing/contradicted/uncertain；引文必须在对应剧情原文。
可记录失败以便修订，但出口必须全satisfied。引文定位与模型判断都不证明文学绝对正确。
另附[反AI味语境复审](prose-risks.md)，不能用字数或关键词齐全替代。

## 命令和兼容

```bash
python3 .agents/skills/novel-director/scripts/novel.py spec-template BOOK
python3 .agents/skills/novel-director/scripts/novel.py spec-check BOOK
python3 .agents/skills/novel-director/scripts/novel.py spec-budget BOOK V01-C01
python3 .agents/skills/novel-director/scripts/novel.py spec-map-check BOOK V01-C01 draft.md --content-map parts.json
python3 .agents/skills/novel-director/scripts/novel.py run-submit BOOK RUN draft.md --content-map parts.json
```

BOOK/RUN换实际路径/返回ID。独立安装用Skill实际目录中的脚本绝对路径。无writing_spec的旧项目保留原签名/流程，
明确spec_not_configured；新Skill正文/修订阶段不许省规格。旧稿诊断/基线初审可保留篇幅不合事实，不能把基线当新合格稿批准。
通过阶段/审稿也不会自动批准、发布或改canon，仍需本次作者对确切候选的明确授权。
