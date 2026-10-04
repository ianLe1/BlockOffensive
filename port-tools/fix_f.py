#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 F：序列化层（Component / ItemStack / NBT 组件 / 颜色）

1.21.1 事实（javap 实证，见 PORT-NOTES.md）：
  * `FriendlyByteBuf` 没有 `writeComponent/readComponent/writeItem/readItem`。
    - Component → `ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC`
      （它是 `StreamCodec<io.netty.buffer.ByteBuf, Component>`，可直接吃 FriendlyByteBuf；
       另外的 STREAM_CODEC 要求 RegistryFriendlyByteBuf，而本模组的包走的是纯 FriendlyByteBuf 垫片）
    - ItemStack → `buf.writeJsonWithCodec(ItemStack.CODEC, stack)` / `buf.readJsonWithCodec(ItemStack.CODEC)`
      （ItemStack 的 STREAM_CODEC 同样要求 RegistryFriendlyByteBuf；本模组包体因此走 JSON codec，
       保真度风险已记入 PORT-NOTES）
  * `FriendlyByteBuf::writeUUID` 这类**方法引用**在 1.21.1 会因为 `writeUUID(ByteBuf,UUID)` 静态重载
    而「引用不明确」，进而让 `writeMap/readMap` 的 K,V 推断失败 ⇒ 换成显式类型 lambda（已用 javac 单独验证）。
  * `ItemStack#getOrCreateTag/getTag/setTag/setHoverName` 随 NBT→DataComponents 一并删除：
    - getOrCreateTag().putX(...) → `CustomData.update(DataComponents.CUSTOM_DATA, stack, tag -> tag.putX(...))`
    - getTag()                   → `stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).copyTag()`
    - setTag(t)                  → `stack.set(DataComponents.CUSTOM_DATA, CustomData.of(t))`
    - setHoverName(c)            → `stack.set(DataComponents.CUSTOM_NAME, c)`
    - ItemStack.isSameItemSameTags(a,b) → `ItemStack.isSameItemSameComponents(a,b)`
  * `TextColor.parseColor(String)` 返回 `DataResult<TextColor>`；`Style.withColor` 只接受 TextColor/ChatFormatting/int
    ⇒ 补 `.result().orElseThrow()`。

只做机械替换 + 补 import，不改玩法逻辑。幂等。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')

STATS = []
CHANGED = set()

# 幂等归一：早期版本的 parseColor 规则会把 `.result().orElseThrow()` 叠加多次
# （下次再跑本脚本时先归一，因此本脚本既可重复运行，也能修复历史上被叠加的产物）。
DOUBLE_ORELSE = re.compile(r'(\.result\(\)\.orElseThrow\(\))+')


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


def find_receiver_start(text, dot):
    """从方法名前的 '.' 往回找 receiver 起点（支持链式调用与括号配对）。"""
    i = dot - 1
    depth = 0
    while i >= 0:
        ch = text[i]
        if ch in ')]}':
            depth += 1
            i -= 1
        elif ch in '([{':
            if depth == 0:
                # 到达外层调用的 '(' —— receiver 从它之后开始
                break
            depth -= 1
            i -= 1
        elif depth > 0:
            i -= 1
        elif ch.isalnum() or ch in '_.$':
            i -= 1
        else:
            break
    return i + 1


def rewrite_call(text, method, transform):
    """对所有 `.method(...)` 调用点调用 transform(recv, args)；返回 None 表示不改。"""
    pat = '.' + method + '('
    out = []
    i = 0
    n = 0
    while True:
        j = text.find(pat, i)
        if j < 0:
            out.append(text[i:])
            break
        # 找匹配的右括号
        m = j + len(pat) - 1          # 指向 '('
        depth = 0
        m2 = m
        while m2 < len(text):
            if text[m2] == '(':
                depth += 1
            elif text[m2] == ')':
                depth -= 1
                if depth == 0:
                    break
            m2 += 1
        k = find_receiver_start(text, j)
        if k >= j:
            # 认不出 receiver（例如字面量/表达式直接跟 .method(）→ 原样跳过，绝不死循环
            out.append(text[i:m2 + 1])
            i = m2 + 1
            continue
        recv = text[k:j]
        args = text[m + 1:m2]
        new = transform(recv, args)
        if new is None:
            out.append(text[i:m2 + 1])
        else:
            out.append(text[i:k])
            out.append(new)
            n += 1
        i = m2 + 1
    return ''.join(out), n


def bump(label, n, rel):
    if n:
        STATS.append('%-52s %d' % (label, n))
        CHANGED.add(rel)


# ── 全局规则 ─────────────────────────────────────────────────────────
def rule_buffers(text):
    n_all = 0

    def t_comp(recv, args):
        return 'ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.encode(%s, %s)' % (recv, args)

    text, n = rewrite_call(text, 'writeComponent', t_comp)
    n_all += n
    STATS.append('%-52s %d' % ('writeComponent -> ComponentSerialization codec', n))

    def t_comp_r(recv, args):
        return 'ComponentSerialization.TRUSTED_CONTEXT_FREE_STREAM_CODEC.decode(%s)' % recv

    text, n = rewrite_call(text, 'readComponent', t_comp_r)
    n_all += n
    STATS.append('%-52s %d' % ('readComponent -> ComponentSerialization codec', n))

    def t_item(recv, args):
        return '%s.writeJsonWithCodec(ItemStack.CODEC, %s)' % (recv, args)

    text, n = rewrite_call(text, 'writeItem', t_item)
    n_all += n
    STATS.append('%-52s %d' % ('writeItem -> writeJsonWithCodec(ItemStack.CODEC)', n))

    def t_item_r(recv, args):
        return '%s.readJsonWithCodec(ItemStack.CODEC)' % recv

    text, n = rewrite_call(text, 'readItem', t_item_r)
    n_all += n
    STATS.append('%-52s %d' % ('readItem -> readJsonWithCodec(ItemStack.CODEC)', n))

    if n_all:
        text = add_import(text, 'net.minecraft.network.chat.ComponentSerialization')
        text = add_import(text, 'net.minecraft.world.item.ItemStack')
    return text, n_all


def rule_write_map_refs(text):
    """FriendlyByteBuf::writeUUID 等在 1.21.1 引用不明确 → 显式类型 lambda。"""
    tot = 0
    for old, new in (
            ('FriendlyByteBuf::writeUUID', '(FriendlyByteBuf b, UUID u) -> b.writeUUID(u)'),
            ('FriendlyByteBuf::writeInt', '(FriendlyByteBuf b, Integer i) -> b.writeInt(i)'),
            ('FriendlyByteBuf::readUUID', '(FriendlyByteBuf b) -> b.readUUID()'),
            ('FriendlyByteBuf::readInt', '(FriendlyByteBuf b) -> b.readInt()'),
    ):
        c = text.count(old)
        if c:
            text = text.replace(old, new)
            STATS.append('%-52s %d' % ('method-ref -> lambda: ' + old.split('::')[1], c))
            tot += c
    return text, tot


def rule_parse_color(text):
    def t(recv, args):
        if recv != 'TextColor':
            return None
        return 'TextColor.parseColor(%s).result().orElseThrow()' % args

    text, n = rewrite_call(text, 'parseColor', t)
    if n:
        STATS.append('%-52s %d' % ('TextColor.parseColor -> .result().orElseThrow()', n))
    return text, n


# ── 仅限指定文件的 NBT / 组件规则 ────────────────────────────────────
def rule_item_nbt(text, rel):
    tot = 0

    def t_get_or_create(recv, args):
        if not recv.endswith('.getOrCreateTag()'):
            return None
        base = recv[:-len('.getOrCreateTag()')]
        return 'CustomData.update(DataComponents.CUSTOM_DATA, %s, tag -> tag.putString(%s))' % (base, args)

    text, n = rewrite_call(text, 'putString', t_get_or_create)
    tot += n
    STATS.append('%-52s %d' % ('getOrCreateTag().putString -> CustomData.update [%s]' % rel, n))

    def t_get_tag(recv, args):
        return '%s.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).copyTag()' % recv

    text, n = rewrite_call(text, 'getTag', t_get_tag)
    tot += n
    STATS.append('%-52s %d' % ('getTag() -> getOrDefault(CUSTOM_DATA).copyTag() [%s]' % rel, n))

    def t_set_tag(recv, args):
        return '%s.set(DataComponents.CUSTOM_DATA, CustomData.of(%s))' % (recv, args)

    text, n = rewrite_call(text, 'setTag', t_set_tag)
    tot += n
    STATS.append('%-52s %d' % ('setTag -> set(CUSTOM_DATA) [%s]' % rel, n))

    def t_hover(recv, args):
        return '%s.set(DataComponents.CUSTOM_NAME, %s)' % (recv, args)

    text, n = rewrite_call(text, 'setHoverName', t_hover)
    tot += n
    STATS.append('%-52s %d' % ('setHoverName -> set(CUSTOM_NAME) [%s]' % rel, n))

    if tot:
        text = add_import(text, 'net.minecraft.core.component.DataComponents')
        text = add_import(text, 'net.minecraft.world.item.component.CustomData')
    return text, tot


def main():
    dry = '--dry' in sys.argv
    files = sorted(os.path.join(b, n)
                   for b, _, ns in os.walk(ROOT) for n in ns if n.endswith('.java'))
    for f in files:
        rel = f.replace(ROOT + '/', '')
        text = orig = open(f, encoding='utf-8').read()
        text = DOUBLE_ORELSE.sub('.result().orElseThrow()', text)

        text, _ = rule_buffers(text)
        text, _ = rule_write_map_refs(text)
        text, _ = rule_parse_color(text)

        if rel.endswith('gametest/ListenerModuleEditorGameTests.java') or \
           rel.endswith('gametest/ShopEditorGameTests.java') or \
           rel.endswith('gametest/ShopRefundGameTests.java'):
            text, _ = rule_item_nbt(text, rel)

        if rel.endswith('server/shop/ShopDropPickupService.java'):
            c = text.count('ItemStack.isSameItemSameTags(')
            if c:
                text = text.replace('ItemStack.isSameItemSameTags(', 'ItemStack.isSameItemSameComponents(')
                STATS.append('%-52s %d' % ('isSameItemSameTags -> isSameItemSameComponents', c))

        # 规则跑完后再次归一：parseColor 规则是「先追加、末尾统一去重」，
        # 因此重跑得到与首次相同的单后缀形态 ⇒ 本脚本幂等、且能自修复历史双写。
        text = DOUBLE_ORELSE.sub('.result().orElseThrow()', text)

        if text != orig:
            CHANGED.add(rel)
            if not dry:
                open(f, 'w', encoding='utf-8').write(text)

    print('== fix_f 命中 ==')
    for s in STATS:
        if not s.rstrip().endswith(' 0'):
            print('  ' + s)
    print('  涉及文件 %d 个' % len(CHANGED))
    for c in sorted(CHANGED):
        print('    ' + c)


if __name__ == '__main__':
    main()
