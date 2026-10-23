# 宿主接入：真实分开调用，而不是一段文本扮演多人

本包继承Python标准库，不绑定新云平台，不自带模型账号。宿主提供独立调用（可使用其已有的子Agent服务或模型API），控制器只做可检查的调度。实际部署必须把同一worker的不同session_key作上下文分区；每次以当前packet替换输入，不自动追加私有全局历史。多个writer角色不等于独立的读者评审样本。

## 编程接口

```python
from pathlib import Path
from ensemble_runtime import start, drive

class YourHostTransport:
    def __init__(self, host):
        self.host = host

    def invoke(self, worker_id: str, session_key: str, packet: dict) -> dict:
        # 对接你已部署宿主的真实接口；以下host.invoke_isolated是应用适配接口，
        # 不是某个SDK现成方法。必须实现独立上下文及禁用额外文件工具。
        return self.host.invoke_isolated(
            worker_id=worker_id,
            context_slot=session_key,
            replace_context=True,
            tools=[],
            system=packet['system'],
            input=packet['input'],
            output_contract=packet['response_contract'],
            request_id=packet['request_id'],
        )

# config/scene为已由主线或作者准备并检查的JSON；不从任意文本自动当成正式Canon。
# created = start(Path('my-story'), config, scene)
# result = drive(Path('my-story'), created['ensemble_id'], YourHostTransport(host),
#                max_calls=8, source='host_supplied')
```

这是明确待实现的宿主适配边界，不能把示例中的host接口说成已经对接的服务。`drive`本身可执行并有FakeTransport的正反测试；本次没有真实模型调用。

注册规则：narrator一个，core:<character_id>每个一个，npc-pool一个。NPC使用同一worker但instance/history的context_slot不同。narrator的resolve和compose不同slot，防止把规划秘密写进正文。网络失败直接报错并停在当前请求；不会偷偷改为单Agent生成。

## CLI（无须编程接口，也能给兼容宿主逐步调度）

```bash
python3 .agents/skills/novel-director/scripts/novel.py ensemble-start STORY \
 --config .agents/skills/novel-director/assets/ensemble-demo/config.json \
 --scene .agents/skills/novel-director/assets/ensemble-demo/scene.json
# 返回ens-开头的实际ID。用返回值替代下面ENS。
python3 .agents/skills/novel-director/scripts/novel.py ensemble-packet STORY ENS
# 宿主将包交给指定worker并把真实响应存为response.json
python3 .agents/skills/novel-director/scripts/novel.py ensemble-respond STORY ENS response.json --source host_supplied
python3 .agents/skills/novel-director/scripts/novel.py ensemble-status STORY ENS
# 重复直到complete，然后只提交候选，原审校与作者批准仍不可跳过。
python3 .agents/skills/novel-director/scripts/novel.py ensemble-handoff STORY ENS
python3 .agents/skills/novel-director/scripts/novel.py ensemble-memory STORY ENS > memory-candidate.json
```

导出的memory-candidate.json含所有人物的分区记忆，只供控制器读取。后续场景显式`--memory memory-candidate.json`，并为对应实例增加steps主观序号。导入同配置、同实例、同历史的先前排练数据；它仍是rehearsal_candidate。跨历史/年龄实例转移必须由作者在新配置中明确重建来源，不能自动继承未来人生。

## 返回契约

actor：request_id, actor_id, speech, action_intent, private_intent, used_fact_ids[], disclosed_fact_ids[]；可选pov_interior。
resolve：request_id, accept(bool), reason, result, observers[], reader_visible(bool), end_scene(bool)。拒绝时result为空、observers为空、reader_visible=false。
compose：request_id, text。text须包含全部已采纳且对POV可见的直接对白；其他文风质量由审稿判断。

调用账本记录被接受的响应，不等于模型供应商账单。host_supplied是来源声明而非远程证明。synthetic_test不能当真实人物Agent写作实测。默认8次调用预算是工程默认，不是最优写作轮数；一次3人各发言一轮场景需要3次角色、3次裁定、1次成稿共7次调用。不在场的角色0次。

ensemble-handoff仍是一场景一候选；V0.8多场景章使用[整章契约](long-form-execution.md)的assembly流程创建一个完整章Run，不声称已自动解决整卷规划。交接中断可能留下未发布的孤立Run；不会自动发布任何内容。并发写受锁保护，异常断电留锁需人工核对后清理，不盲目删除锁。
