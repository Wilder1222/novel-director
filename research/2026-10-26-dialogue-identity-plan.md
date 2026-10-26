# 人物对白依据与表达习惯：方案

## contracts
源码增补，当前发布标识保持0.12.0/0.4.2，不构建安装或部署。独立方案审查已退修共享profile的粒度问题，本版将简报/研究的profile工作假设明确调整为instances中的可选speech_style，按instance_id/history_id/年龄边界供给，避免同一人物未来习惯提前可见。profiles仍仅原有字段，不接受speech_style；旧schema0.7配置在新源码中保持兼容。speech_style仅允许personality、baseline_tone、verbal_habits三个非空字符串及catchphrases数组；全都可省略，空对象/空数组允许表示无额外资料。口头禅每项仅phrase/when/avoid_when三项非空字符串，最多8项且phrase去首尾空白后唯一，不准私有配置执行正则/工具。

actor.input仅在本实例提供时获得自己的speech_style深拷贝，不查其它实例、不回退共享profile或合并其它历史样式。实际提示将它与profile.voice/values/limits、goal、relationship_view、最近已观察事件及自身既有记忆共同用于选择说话对象、称呼/礼貌分寸、语体、句长、直接或回避、当场语气和口癖；关系不对称，任务不强迫扭曲人格。常态语气不同于当场情绪，口头禅有适用/抑制条件，可用、变体或不出现，不能考勤或人人套同一句。缺少资料不补发明关系/习惯。

## sequence
brief→research→implementation_plan先真实独立审查。随后新增失败测试，修改ensemble_runtime.py可选字段验证与actor指令，保证不新增给resolve/compose/整章的私密投影，不扩大响应Schema或伪造人物后果。细化prose_risks.flattened_voice及editor指令，公共语料同步到1.4.0并增4例至52例，覆盖对象关系、任务/人格、口癖过用与不使用仍合理；同步模板、角色配置、两Skill、参考与README。

实现后先相关回归、完整unittest与实际CLI/配置调用；语义例和实现由实际独立任务审查。阶段绑定实际源码状态/日志，失败修当前版本，不放宽原串、审批和隐私边界、不创建历史软件备份。完成六阶段后写真实STATUS与checkpoint，host thread ID若未返回仍为null。

## tests
正例：旧配置继续通过；带完整/部分speech_style的核心与NPC包仅含自己的实例样式；配置与packet深拷贝不互相污染。更换自己的goal、relationship_view、对方已裁定发言后包内容/请求摘要更新，同时保留相同稳定声线；同一character_id在H0与H1两个实例各设不同私密口癖，H0.actor只收到H0样式，H1口癖不出现在包中，无本实例样式时也不回退H1；不同实例记忆仍不复用。验证不见另一人物口癖、未来知识或director_goal；共享profile若填speech_style明确拒绝。

反例：未知字段、错误类型/空字符串、缺口头禅触发条件、重复phrase和超过8项均拒绝；未提供speech_style不造默认口癖。resolve不收到speech_style/关系私密总账，compose/整章只保留实际采纳speech；未说出的私密口癖不进入包，已采纳口癖及标点/重复不擅改。编辑零命中也明确核关系/任务/性格/常态与当场语气、口头禅条件，不因没有口癖而判不合格。既有视角、原串锁、Run/阶段及包边界全量回归。

## compatibility
不改writing_spec.py核验器，现有dialogue_context/dialogue_embodiment必审契约承载语境细化。语料categories与代码CATEGORIES同步，语料/检查器SHA自然使旧报告和绑定生产依赖过期，按既有规则重建，不补签。可选字段只在新的场景实例配置中启用，旧正式人物文件不自动迁移；新增习惯为候选材料，不意味着作者已确认Canon。

样式包含人物私密资料，只属于对应actor；不为审稿便利自动投影给narrator或其它人物，不把关系看法当双方真相。编辑对照由主会话按已有安全流程提供。测试证明契约、过滤和可追溯性，不证明模型确实写得自然；当前无法严格人物隔离，测试采用明确合成夹具，不冒称真实角色执行。本次仍不更新安装缓存/网站、不提交push、不修改小说。
