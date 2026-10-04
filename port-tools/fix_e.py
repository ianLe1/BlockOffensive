#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 E：把 DistExecutor 全部换成自建的 ClientPacketExecutor/ClientPacketRegistry。

NeoForge 1.21 删除了 `net.neoforged.fml.DistExecutor`。fpsmatch 移植时定的替代方案是
「common 侧只调 ClientPacketExecutor.execute(Supplier<PayloadContext>, packet)，
 真正的客户端类只在客户端加载的 BOClientPacketRegistrar 里出现」。
本脚本做机械替换 + 接线，不做任何逻辑改写：
  1) 6 个 S2C 包的 handle：删掉 enqueueWork(DistExecutor…) + setPacketHandled，换成一行 execute(...)
  2) CSScoreboardSync.apply 由 private 改 public（注册表要从外部引用方法引用）
  3) TestItem 的 DistExecutor 调用换成直接调用（仍裹 pLevel.isClientSide 守卫）
  4) BlockOffensive.java 删掉已无用的 DistExecutor import
  5) BOClientBootstrap.onClientSetup(RegisterKeyMappingsEvent) 里加 BOClientPacketRegistrar.register()
幂等：若目标写法已存在且旧写法已消失，视为已应用。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')
J = os.path.join(ROOT, 'net', 'ptcrys', 'blockoffensive')

EXEC_IMP_OLD = 'import net.neoforged.fml.DistExecutor;'
EXEC_IMP_NEW = 'import net.ptcrys.blockoffensive.net.ClientPacketExecutor;'


def read(rel):
    with open(os.path.join(J, rel), encoding='utf-8') as fh:
        return fh.read()


def write(rel, text):
    with open(os.path.join(J, rel), 'w', encoding='utf-8') as fh:
        fh.write(text)


def sub1(text, pattern, repl, label, stats, expect=1):
    """按计数替换；已应用过则视为通过。"""
    n = len(re.findall(pattern, text, re.M | re.S))
    if n == 0:
        return text, False
    if expect is not None and n != expect:
        raise SystemExit('!! %s 命中数 %d != 期望 %d' % (label, n, expect))
    text = re.sub(pattern, repl, text, flags=re.M | re.S)
    stats.append('%-46s %d' % (label, n))
    return text, True


# ── 1) 六个 S2C 包：enqueueWork(DistExecutor) -> ClientPacketExecutor.execute ──
PKT = [
    # (相对路径, 旧的 enqueueWork 段(正则), 新的调用, handle 里 Supplier 参数名, 是否用 packet 变量)
    ('net/spec/SpectatorRosterS2CPacket.java',
     r'^(\s*)ctx\.get\(\)\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(Dist\.CLIENT, \(\) -> \(\) -> CSSpectatorRoster\.getInstance\(\)\.accept\(this\)\)\);\s*\n\s*ctx\.get\(\)\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(ctx, this);'),
    ('net/vote/VoteSyncS2CPacket.java',
     r'^(\s*)ctx\.get\(\)\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(Dist\.CLIENT, \(\) -> \(\) -> CSVoteHud\.getInstance\(\)\.accept\(this\)\)\);\s*\n\s*ctx\.get\(\)\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(ctx, this);'),
    ('net/shop/ShopNearbyDropsS2CPacket.java',
     r'^(\s*)PayloadContext context = contextSupplier\.get\(\);\s*\n\s*context\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(\s*\n\s*Dist\.CLIENT, \(\) -> \(\) -> ShopDropClientState\.acceptNearby\(this\)\)\);\s*\n\s*context\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(contextSupplier, this);'),
    ('net/shop/ShopDropPickupResultS2CPacket.java',
     r'^(\s*)PayloadContext context = contextSupplier\.get\(\);\s*\n\s*context\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(\s*\n\s*Dist\.CLIENT, \(\) -> \(\) -> ShopDropClientState\.acceptResult\(this\)\)\);\s*\n\s*context\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(contextSupplier, this);'),
    ('intro/net/IntroSequenceS2CPacket.java',
     r'^(\s*)PayloadContext ctx = context\.get\(\);\s*\n\s*ctx\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(Dist\.CLIENT, \(\) -> \(\) -> IntroClientController\.accept\(packet\)\)\);\s*\n\s*ctx\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(context, packet);'),
    ('net/CSScoreboardSync.java',
     r'^(\s*)var context = supplier\.get\(\);\s*\n\s*context\.enqueueWork\(\(\) -> DistExecutor\.unsafeRunWhenOn\(Dist\.CLIENT, \(\) -> this::apply\)\);\s*\n\s*context\.setPacketHandled\(true\);',
     r'\1ClientPacketExecutor.execute(supplier, this);'),
]



def _already_applied():
    """幂等门禁：DistExecutor 替换确已完成时整体跳过（重跑只打「已应用」噪音）。"""
    for rel in ('net/ClientPacketExecutor.java', 'net/ClientPacketRegistry.java',
                'client/net/BOClientPacketRegistrar.java'):
        if not os.path.exists(os.path.join(J, rel)):
            return False
    return ('ClientAccess.openShop()' in read('item/test/TestItem.java')
            and 'DistExecutor' not in read('net/spec/SpectatorRosterS2CPacket.java'))


def main():
    dry = '--dry' in sys.argv
    stats = []
    changed = []
    if _already_applied():
        print('== fix_e 命中 ==\n  已全部应用，跳过（幂等门禁）')
        return

    for rel, pat, repl in PKT:
        text = read(rel)
        text, hit = sub1(text, pat, repl, 'replace DistExecutor: ' + rel, stats, expect=1)
        if not hit:
            stats.append('%-46s (已应用)' % ('replace DistExecutor: ' + rel))
        if EXEC_IMP_OLD in text:
            text = text.replace(EXEC_IMP_OLD, EXEC_IMP_NEW)
            stats.append('%-46s 1' % ('import -> ClientPacketExecutor: ' + rel))
        elif EXEC_IMP_NEW not in text:
            raise SystemExit('!! %s 既没有 DistExecutor import 也没有 ClientPacketExecutor import' % rel)
        if not dry:
            write(rel, text)
        changed.append(rel)

    # ── 2) CSScoreboardSync.apply private -> public ──────────────────
    rel = 'net/CSScoreboardSync.java'
    text = read(rel)
    text2, hit = sub1(text, r'^(\s*)private void apply\(\)',
                      r'\1public void apply()', 'CSScoreboardSync.apply -> public', stats, expect=1)
    if not hit:
        stats.append('%-46s (已应用)' % 'CSScoreboardSync.apply -> public')
    if text2 != text and not dry:
        write(rel, text2)

    # ── 3) TestItem：DistExecutor -> 直接调用（守卫保留）────────────
    rel = 'item/test/TestItem.java'
    text = read(rel)
    text2, hit = sub1(text,
                      r'^(\s*)net\.neoforged\.fml\.DistExecutor\.unsafeRunWhenOn\(net\.neoforged\.api\.distmarker\.Dist\.CLIENT,\s*\n\s*\(\) -> ClientAccess::openShop\);',
                      r'\1ClientAccess.openShop();', 'TestItem: DistExecutor -> ClientAccess.openShop()', stats, expect=1)
    if not hit:
        stats.append('%-46s (已应用)' % 'TestItem: DistExecutor -> ClientAccess.openShop()')
    if text2 != text and not dry:
        write(rel, text2)

    # ── 4) BlockOffensive.java 删无用 import ────────────────────────
    rel = 'BlockOffensive.java'
    text = read(rel)
    if EXEC_IMP_OLD in text:
        text = text.replace(EXEC_IMP_OLD + '\n', '')
        stats.append('%-46s 1' % 'BlockOffensive: 删 DistExecutor import')
        if not dry:
            write(rel, text)

    # ── 5) BOClientBootstrap 接线 ───────────────────────────────────
    rel = 'client/BOClientBootstrap.java'
    text = read(rel)
    imp = 'import net.ptcrys.blockoffensive.client.net.BOClientPacketRegistrar;'
    if imp not in text:
        anchor = 'import net.ptcrys.blockoffensive.client.renderer.C4Renderer;'
        if anchor not in text:
            raise SystemExit('!! BOClientBootstrap 找不到插入 import 的锚点')
        text = text.replace(anchor, imp + '\n' + anchor)
        stats.append('%-46s 1' % 'BOClientBootstrap: +import BOClientPacketRegistrar')
    call = '        BOClientPacketRegistrar.register();'
    if call not in text:
        anchor = '        FPSMGameHudManager.INSTANCE.registerHud("csdm", CSGameHud.getInstance());'
        if anchor not in text:
            raise SystemExit('!! BOClientBootstrap 找不到插入 register() 的锚点')
        text = text.replace(anchor, anchor + '\n' + call)
        stats.append('%-46s 1' % 'BOClientBootstrap: +BOClientPacketRegistrar.register()')
    if not dry:
        write(rel, text)

    print('== fix_e 命中 ==')
    for s in stats:
        print('  ' + s)
    print('  涉及文件 %d 个' % len(set(changed)))


if __name__ == '__main__':
    main()
