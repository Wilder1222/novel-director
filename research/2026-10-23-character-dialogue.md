# 人物称呼与情境对白：实施前研究及方案

本文件保留实施前研究与方案时点；文中“待采/待审/正在”等为当时状态，不冒称当前进度。当前真实采用范围与纠正后复核结果见[细读索引](REFERENCE-INDEX.md)及[指定参考进度](REQUESTED-REFERENCES.md)，实施后验证另有实际回执。

日期2026-10-23。承接开场/分卷与天蚕土豆排除升级；作者追加原话：「人物名字强制全名，绰号，昵称，非特殊不好用一个姓作为一个人」「人物角色说话要根据人设，场景，情绪，人物关系等因素来决定，说话要口语化，不要过于剧本化或者呆板」。这两项是明确作者偏好，不包装成所有文学作品的通用定律。当前无正式人物/正文，只改创作工具与抽象已确认偏好。

## 一手方法与样本边界

本次实际打开Writing Excuses 10.38完整相关讨论：https://writingexcuses.com/writing-excuses-10-38-how-does-context-shape-dialog/ 。同样一句话的含义受场景、对象、动机、情绪和动作影响；逐句塞动作会干扰对话，机械句式和替作者传信息会使对白僵硬。其英语小说与漫画教学经验支持条件化判断，不能推出中文固定句长、语气词数或每几句一动作的硬配额。

Brandon Sanderson官方FAQ：https://faq.brandonsanderson.com/knowledge-base/do-you-have-advice-about-dialogue/ ，实际全文阅读。以措辞、句长和说话习惯区分声音；观察真实口语但不要机械誊录。去掉标签辨人可作练习，正式稿仍需要必要的说话归属，不能据此删尽名字。

官方2025讲课#6（2025-03-04）：https://www.brandonsanderson.com/blogs/blog/customizing-your-character-brandon-sandersons-writing-lecture-6-2025 ，实际读取动机/人格/价值及character voice相关部分。相同动机可有不同表达，语体随交谈对象改变，不以学历/职业刻板标签决定台词。本轮不声称通读其全部课程。

Writing Excuses 9.19：https://writingexcuses.com/writing-excuses-9-19-showing-emotion/ ，实际读相关讨论。内心情绪与公开表现有区别，克制/掩饰也有情感作用，题材和叙述距离影响表达。不能把“生气”统一写成吼叫或把紧张统一写成结巴。

此前同次研究已实际核对wgwtest/novel-writing（story-outline-and-causal-summary、scene-causality-and-agency）和JeroTan/novel-writer-english（forgotten-elements），URL见2026-10-22-opening-volume.md。本轮复用其因果/人物知识和检查边界，不复制代码；没有重跑外部测试、重核license或把旧维护/CI记录当本轮事实。

现有真实九书逐章记录支持：同一个人的表达会随药物供给/制度身份/关系信任改变，称呼与身份揭示需保留时点；各书叙述偏好不同不能一概视为范文。永夜20章的两执行者已经完整阅读，第二执行者正在核其20章析/3链/6卡，未经复核不入方法库。世界维度看身份制度和话语权；情节看对白行为目的及后果；人物看知识/目标/声线；情感看当场感受、抑制与关系变化。不是流行作品成功率实验。

## 现有实现实查与缺口

演员packet已有profile.name/voice、age、goal、private_fear、relationship_view、当时knowledge、observations、自身已接收反馈。没有必要把整份narrator writing_profile送给演员，也不能额外读取他人心理。当前ACTOR_INSTRUCTION未明确称呼与情境口语；只将偏好存profile会停在compose，演员已生成的speech未必遵守。

resolve处理提案后拒绝也会推进turn，并非自动原地重试；对白问题应在允许的后续演员轮次或新排练修正，预算耗尽照实停止。compose及整章汇编须逐字保留已采纳可见speech，不能偷偷把一个姓改全名、把口语改书面语或反向改坏；若需改，重新排练/相应修订流程。

writing_spec.CRAFT当前没有专门称呼/对白目标，可增加两项，复用真实正文引文与漏项/错scope/partial阻断。prose_risks.flattened_voice已有八类语义检查，可扩其描述与原创案例，不新增作者身份鉴定或简单“姓氏正则删词”。

## 具体契约

默认使用获准显示的全名、已设定且当前人物可知的绰号/昵称。已用别称应能回指同一人物，不能为避重复轮换新称谓。单姓称人只在有具体依据的特殊语境使用并解释其功能；“欧阳”可能复姓，“陈”也可能恰是已设单字名字，不能凭字数自动裁定。代词、清楚的职业/关系称谓不被禁止，不要求每句重复全名。真实姓名尚未知时使用当前获准的代称/身份，不从后台补真名，也不现编昵称。

对白先考虑：这人平时如何表达、此刻想做什么、和谁说、现场谁听得到、情绪与身体状态如何、双方关系及权力/熟悉程度怎样、哪些信息能说。自然口语包含合适的省略、接话、打断、犹豫、转移、沉默和潜台词，但不机械给每句加“啊呢吧”、现代网络梗、方言或舞台动作。正式汇报、礼仪场合、克制长句也可合理；不把“口语化”等同粗俗、人人轻佻或全说短句。无对白章节不强行补对白。

## 方案顺序、产物与验收

先真实brief/research/implementation_plan审查，再改本轮新增逻辑。1）扩演员/裁定/成稿指令和角色模板，用现有受限资料条件化表达，不向演员投影整份风格包；2）新增character_naming/dialogue_context两个CRAFT目标，scene_plan交代说话目的/关系/情绪与称呼依据，editorial举实际语句；3）扩flattened_voice与4条原创语境案例，保留例外与原意，风险定位不是自动不合格；4）本书rules保存作者明确偏好，通用模板候选，narration_origin区分tool_default/author_confirmed/旧记录未注明，旧字段兼容不倒填确认；5）全量回归、公开包与安装验证后交付；新五书参考由父任务独立继续，达不到20章不冒充完成。

正向验证实际actor system含适用要求，并沿现有profile.voice/当前关系/观察行事；默认人称来源传到compose；已设别称/复姓/未知身份代称及合理正式台词应被语义评估保留。反向验证演员包不含narrator profile/未来秘密，漏掉新CRAFT项阻断，compose擅改已采纳speech拒绝，无依据单姓/临时昵称/所有对象同腔调/人物私密说明须退修。有限微型成对语义样本交不同执行者，不把合成测试或模型意见称读者验收。

兼容：不改角色JSON schema或扩大权限，不热迁移已冻结Run；新增指令/CRAFT/语料/项目profile会使旧流程依赖过期，显式替代重核，不回填历史PASS。不动正式canon/正文，不push或发布小说，安装不新建历史备份；此前被拒的软件旧清理不换工具重试。

## 实施中独立复审发现与先行修复方案

实际只读代码审查 /root/opening_arc_map 复现：单场compose仅用子串包含检查，两句已采纳speech可倒排，相同speech两次可只出现一次仍放行；整章assembly已有游标顺序检查。新增test_scene_compose_preserves_speech_order_and_each_repeated_occurrence实际先红：1测试的倒排/重复两个子例均FAIL（未抛ValueError，exit1，1.177秒）。本次先记录方案再修逻辑：沿可见events顺序，以find(speech,cursor)逐次消耗不同且不重叠的出现位置，找不到拒绝；空speech跳过，保持逐字保护和既有限知过滤，不增加人物信息，不自动改稿。修后跑相关及完整回归，并交原独立审查者重核。
