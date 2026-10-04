#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 C：TickEvent 家族重组 + 生物受伤/攻击事件合并 + Registry#getValue→get。

1.21.1 事实（javap 实证，见 PORT-NOTES.md）：
  * `TickEvent` 整个类被拆成 `…event.tick.{ServerTickEvent,PlayerTickEvent,LevelTickEvent,EntityTickEvent}`
    与 `…client.event.ClientTickEvent`，各自只有嵌套的 `Pre`/`Post`，**没有 phase 字段**。
    上游 `if (x.phase != TickEvent.Phase.END) return;` 一律等价于「换成 .Post 后把这段判定删掉」。
  * `LivingHurtEvent` 与 `LivingAttackEvent` 都不存在，合并为 `LivingIncomingDamageEvent`。
  * `Registry#getValue(ResourceLocation)` 改名为 `get`。
幂等：已改过的不会再命中。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')

TICK_MAP = [
    ('TickEvent.ClientTickEvent', 'ClientTickEvent.Post', 'net.neoforged.neoforge.client.event.ClientTickEvent'),
    ('TickEvent.ServerTickEvent', 'ServerTickEvent.Post', 'net.neoforged.neoforge.event.tick.ServerTickEvent'),
    ('TickEvent.PlayerTickEvent', 'PlayerTickEvent.Post', 'net.neoforged.neoforge.event.tick.PlayerTickEvent'),
    ('TickEvent.LevelTickEvent', 'LevelTickEvent.Post', 'net.neoforged.neoforge.event.tick.LevelTickEvent'),
    ('TickEvent.EntityTickEvent', 'EntityTickEvent.Post', 'net.neoforged.neoforge.event.tick.EntityTickEvent'),
]


def add_import(text, imp):
    line = 'import %s;' % imp
    if line in text:
        return text
    lines = text.split('\n')
    idxs = [i for i, l in enumerate(lines) if l.startswith('import ')]
    if not idxs:
        return text
    for i in idxs:
        if lines[i] > line:
            lines.insert(i, line)
            return '\n'.join(lines)
    lines.insert(idxs[-1] + 1, line)
    return '\n'.join(lines)


def drop_import(text, imp):
    return text.replace('import %s;\n' % imp, '')


def java_files():
    for base, _, names in os.walk(ROOT):
        for n in names:
            if n.endswith('.java'):
                yield os.path.join(base, n)


def main():
    dry = '--dry' in sys.argv
    stats = {}
    leftovers = []

    def bump(k, n=1):
        stats[k] = stats.get(k, 0) + n

    for f in sorted(java_files()):
        text = open(f, encoding='utf-8').read()
        orig = text
        rel = f.replace(ROOT + '/', '')

        # ── C1) TickEvent phase 判定清理（在类型替换之前，按上游写法逐种消解）──
        if 'TickEvent' in text:
            n0 = text.count('TickEvent')
            # if (x.phase != TickEvent.Phase.END) { return; }
            text = re.sub(r'if \((\w+)\.phase != TickEvent\.Phase\.END\) \{\s*\n\s*return;\s*\n\s*\}\n', '', text)
            text = re.sub(r'if \((\w+)\.phase != TickEvent\.Phase\.END\) \{\s*return;\s*\}\s*\n', '', text)
            text = re.sub(r'if \((\w+)\.phase != TickEvent\.Phase\.END\)\s*return;\n', '', text)
            # x.phase != TickEvent.Phase.END || <rest>   ->  <rest>
            text = re.sub(r'(\w+)\.phase != TickEvent\.Phase\.END \|\| ', '', text)
            # x.phase == TickEvent.Phase.END && <rest>   ->  <rest>
            text = re.sub(r'(\w+)\.phase == TickEvent\.Phase\.END && ', '', text)
            # <rest> || x.phase != TickEvent.Phase.END   ->  <rest>
            text = re.sub(r' \|\| (\w+)\.phase != TickEvent\.Phase\.END', '', text)
            if text != orig:
                bump('TickEvent phase 判定清理', n0 - text.count('TickEvent'))

            # 类型替换
            used = []
            for old, new, imp in TICK_MAP:
                if old in text:
                    bump('%s -> %s' % (old, new), text.count(old))
                    text = text.replace(old, new)
                    used.append(imp)
            if used:
                text = drop_import(text, 'net.neoforged.neoforge.event.TickEvent')
                for imp in used:
                    text = add_import(text, imp)

        # ── C2) LivingHurtEvent / LivingAttackEvent -> LivingIncomingDamageEvent ──
        if 'LivingHurtEvent' in text or 'LivingAttackEvent' in text:
            bump('LivingHurt/AttackEvent -> LivingIncomingDamageEvent',
                 text.count('LivingHurtEvent') + text.count('LivingAttackEvent'))
            for old in ('net.neoforged.neoforge.event.entity.living.LivingHurtEvent',
                        'net.neoforged.neoforge.event.entity.living.LivingAttackEvent'):
                text = drop_import(text, old)
            text = text.replace('LivingHurtEvent', 'LivingIncomingDamageEvent')
            text = text.replace('LivingAttackEvent', 'LivingIncomingDamageEvent')
            text = add_import(text, 'net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent')

        # ── C3) Registry#getValue -> get ────────────────────────────────
        text, c = re.subn(r'\b(BuiltInRegistries\.\w+)\.getValue\(', r'\1.get(', text)
        if c:
            bump('BuiltInRegistries.*.getValue->get', c)

        if text != orig:
            if not dry:
                open(f, 'w', encoding='utf-8').write(text)
            if re.search(r'\.phase\b', text):
                leftovers.append(rel)

    print('== fix_c 命中 ==')
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print('  %-58s %d' % (k, v))
    if leftovers:
        print('== 仍需人工看的残留 .phase 文件 ==')
        for r in leftovers:
            print('   ' + r)


if __name__ == '__main__':
    main()
