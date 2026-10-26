# 自述、练习与晋升铺垫：实施方案

## contracts

新增interiority-progression.md给出人物自述、练习细节、晋升前中后、铺垫兑现及适用例外。自述是当前视角的回想/感知/判断与取舍，不默认第一人称或通篇自我介绍。练习写清目标和基线、尝试、实际反馈、理解/方法调整与有限结果；晋升核前证/门槛、过程中的选择和现象、具体前后差异、稳定程度和残留限制。按已有设定选择有作用细节，不强迫每次失败、受伤、异象或升级。已稳定重复可概述；关键变化按章卡详细展开，不固定字数/比例/频率。

主会话用已有writing_spec.detail_requirements及setups建立有关章节的具体要求、plant/reinforce/payoff和真实prior引文，不加全题材强制字段。actor可提自身练习动作与基于可公开知识的pov_interior，不自行宣告成功；resolve依已许可规则裁定可见局部结果，不把个人体感确认为客观进阶；compose/chapter_compose共用INTERIORITY_PROGRESSION指令，仅用本包已裁定可见事件和许可POV内心组织细节。editor零命中仍审空泛过程、越权解释/升级、情绪重复和铺垫因果；沿八类报告给范围、证据和修订方向，不按术语数量评分。

## sequence

brief、research、implementation_plan当前实际独立审查通过后，先写失败测试，再更新实际actor/resolve/compose/整章/editor提示及两Skill/角色模板/参考路由；保留已有数据Schema、语料1.5.0/56例和writing_spec.py字节。本轮四组原创正反教学例放新参考，独立完整审读，不用增加关键词语料制造自动检测能力。对新测试先记录红灯，再相关回归、全量测试与真实CLI，命令与退出码从执行时记录。刷新当前公共源清单，最终核源SHA/清单/阶段，再保存STATUS/checkpoint。

## tests

实际actor/resolve/compose/chapter_compose包载入各自规则，不将主会话未来答案或私密总账加入角色包。许可POV内心进入场景compose的可见事件；整章沿用已完成场景正文的许可内心，不新增内心元数据投影，accepted_events仍不含原始pov_interior。关闭allow_pov_interior、非POV角色、POV不在observers或reader_visible=false均不得通过场景内心投影泄露，涉及不可公开knowledge的pov_interior仍拒绝；夹具成稿只使用投影后信息，确认整章不会重新引入被过滤字段，不将该测试冒称自由正文语义审查。零命中editor仍含成长过程/铺垫审读；uncertain仍阻断。只检测接口/权限/报告契约，不宣称自动辨别功法是否合理；已有铺垫prior/原文门槛和对白锁通过相关及全量回归。

## compatibility

仅Director0.12.0/Studio0.4.2当前源码增补，不安装、构建旧版备份、push或部署，不改作者小说、Canon、正式功法/境界或批准正文。沿用八类/语料和既有公开内心过滤，不把private_intent或完整实例知识送给成稿；未知机制由主会话提出候选/补资料，不能绕过现有宿主能力门槛。旧绑定生产资料/报告如过期需重建，不能把前轮192项或已安装版本称本轮验证。没有待用户批准的具体小说设定。
