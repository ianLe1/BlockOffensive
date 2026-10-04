#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 A：Forge -> NeoForge 的**纯机械**包名/类名替换。

只做「语义等价、零判断」的替换；每一段都幂等可重跑。
判断类的问题（网络 SimpleChannel、TickEvent 重组、ForgeGui、
PhysicsMod/javazoom 缺依赖、@Mod 构造器签名）留给后续批次。

关键顺序约定：
  * 最具体的包名先替换（registries 的四个特例、common 的两个特例、
    fml.common.Mod.EventBusSubscriber），最后才是通用前缀与裸类名。
  * 裸类名（MinecraftForge / ForgeConfigSpec / ForgeRegistries / RegistryObject）
    必须放在包名替换**之后**，否则会把 import 路径改成不存在的类。
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'java')

# ── 1) 包名前缀替换（有序，最具体在前）─────────────────────────────
PKG_RULES = [
    # registries 特例：DeferredRegister/RegistryObject 搬家，ForgeRegistries 被 BuiltInRegistries 取代
    ('net.minecraftforge.registries.DeferredRegister', 'net.neoforged.neoforge.registries.DeferredRegister'),
    ('net.minecraftforge.registries.RegistryObject', 'net.neoforged.neoforge.registries.DeferredHolder'),
    ('net.minecraftforge.registries.ForgeRegistries', 'net.minecraft.core.registries.BuiltInRegistries'),
    ('net.minecraftforge.registries.IForgeRegistryEntry', 'net.minecraft.core.Registry'),
    ('net.minecraftforge.registries.', 'net.neoforged.neoforge.registries.'),
    # common 特例
    ('net.minecraftforge.common.ForgeConfigSpec', 'net.neoforged.neoforge.common.ModConfigSpec'),
    ('net.minecraftforge.common.MinecraftForge', 'net.neoforged.neoforge.common.NeoForge'),
    ('net.minecraftforge.common.', 'net.neoforged.neoforge.common.'),
    # 事件总线 / 分发标记
    ('net.minecraftforge.api.distmarker.', 'net.neoforged.api.distmarker.'),
    ('net.minecraftforge.eventbus.api.', 'net.neoforged.bus.api.'),
    # @Mod 与 @EventBusSubscriber
    ('net.minecraftforge.fml.common.Mod.EventBusSubscriber', 'net.neoforged.fml.common.EventBusSubscriber'),
    ('net.minecraftforge.fml.common.Mod', 'net.neoforged.fml.common.Mod'),
    ('net.minecraftforge.fml.', 'net.neoforged.fml.'),
    # 其余通用前缀
    ('net.minecraftforge.network.', 'net.neoforged.neoforge.network.'),
    ('net.minecraftforge.event.', 'net.neoforged.neoforge.event.'),
    ('net.minecraftforge.client.', 'net.neoforged.neoforge.client.'),
    ('net.minecraftforge.gametest.', 'net.neoforged.neoforge.gametest.'),
    ('net.minecraftforge.', 'net.neoforged.neoforge.'),
]

# ── 2) 裸类名替换 ────────────────────────────────────────────────
BARE_RULES = [
    (r'\bMinecraftForge\b', 'NeoForge'),
    (r'\bForgeConfigSpec\b', 'ModConfigSpec'),
    (r'\bForgeRegistries\b', 'BuiltInRegistries'),
    # BuiltInRegistries 的成员是单数形式
    (r'\bBuiltInRegistries\.ITEMS\b', 'BuiltInRegistries.ITEM'),
    (r'\bBuiltInRegistries\.SOUND_EVENTS\b', 'BuiltInRegistries.SOUND_EVENT'),
    (r'\bBuiltInRegistries\.ENTITY_TYPES\b', 'BuiltInRegistries.ENTITY_TYPE'),
    (r'\bBuiltInRegistries\.PARTICLES\b', 'BuiltInRegistries.PARTICLE_TYPE'),
    (r'\bBuiltInRegistries\.MOB_EFFECTS\b', 'BuiltInRegistries.MOB_EFFECT'),
    (r'\bBuiltInRegistries\.FLUIDS\b', 'BuiltInRegistries.FLUID'),
    (r'\bBuiltInRegistries\.ATTRIBUTES\b', 'BuiltInRegistries.ATTRIBUTE'),
    (r'\bBuiltInRegistries\.MENU_TYPES\b', 'BuiltInRegistries.MENU'),
    (r'\bBuiltInRegistries\.RECIPE_TYPES\b', 'BuiltInRegistries.RECIPE_TYPE'),
    (r'\bBuiltInRegistries\.RECIPE_SERIALIZERS\b', 'BuiltInRegistries.RECIPE_SERIALIZER'),
    (r'\bBuiltInRegistries\.CREATIVE_MODE_TABS\b', 'BuiltInRegistries.CREATIVE_MODE_TAB'),
]

# RegistryObject<X> -> DeferredHolder<X, X>（必须在裸类名替换前）
REGISTRY_OBJECT = re.compile(r'\bRegistryObject\s*<\s*([^,<>]+?)\s*>')


def add_import(text, imp):
    line = 'import %s;' % imp
    if line in text:
        return text
    lines = text.split('\n')
    idxs = [i for i, l in enumerate(lines) if l.startswith('import ')]
    if idxs:
        for i in idxs:
            if lines[i] > line:
                lines.insert(i, line)
                return '\n'.join(lines)
        lines.insert(idxs[-1] + 1, line)
        return '\n'.join(lines)
    return text


def java_files():
    for base, _, names in os.walk(ROOT):
        for n in names:
            if n.endswith('.java'):
                yield os.path.join(base, n)


def main():
    dry = '--dry' in sys.argv
    hits = {}
    changed = []
    for f in sorted(java_files()):
        text = open(f, encoding='utf-8').read()
        orig = text
        local = {}

        # 1) 包名前缀
        for old, new in PKG_RULES:
            if old in text:
                local[old] = text.count(old)
                text = text.replace(old, new)

        # 2) RegistryObject<T> -> DeferredHolder<T, T>
        text, c = REGISTRY_OBJECT.subn(lambda m: 'DeferredHolder<%s, %s>' % (m.group(1), m.group(1)), text)
        if c:
            local['RegistryObject<T>'] = c

        # 3) 裸类名
        for pat, new in BARE_RULES:
            text, c = re.subn(pat, new, text)
            if c:
                local[pat] = c

        # 4) @Mod.EventBusSubscriber -> @EventBusSubscriber（含 Bus.FORGE -> Bus.GAME）
        if 'Mod.EventBusSubscriber' in text:
            local['Mod.EventBusSubscriber'] = text.count('Mod.EventBusSubscriber')
            text = text.replace('Mod.EventBusSubscriber', 'EventBusSubscriber')
            text = text.replace('EventBusSubscriber.Bus.FORGE', 'EventBusSubscriber.Bus.GAME')
            text = add_import(text, 'net.neoforged.fml.common.EventBusSubscriber')

        # 5) 补 @Mod 的 import（原来靠 net.minecraftforge.fml.common.Mod，已被改名）
        if '@Mod(' in text or '@Mod\n' in text:
            text = add_import(text, 'net.neoforged.fml.common.Mod')

        if text != orig:
            if not dry:
                open(f, 'w', encoding='utf-8').write(text)
            changed.append((f.replace(ROOT + '/', ''), local))
            for k, v in local.items():
                hits[k] = hits.get(k, 0) + v

    print('== 替换命中总表 ==')
    for k, v in sorted(hits.items(), key=lambda kv: -kv[1]):
        print('  %-70s %d' % (k, v))
    print('== 修改文件 %d 个 ==' % len(changed))
    for f, local in changed[:40]:
        print('   %-90s %s' % (f, local))
    if len(changed) > 40:
        print('   ... 其余 %d 个同上模式' % (len(changed) - 40))


if __name__ == '__main__':
    main()
