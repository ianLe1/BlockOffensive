#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 B：网络层 Forge SimpleChannel -> NeoForge CustomPacketPayload。

BlockOffensive 上游走的是 Forge 的
  INSTANCE.send(PacketDistributor.PLAYER.with(() -> player), packet)
  INSTANCE.sendToServer(packet)
  + 包类里 handle(Supplier<NetworkEvent.Context>)
1.21.1 的 NeoForge 已经没有 SimpleChannel / NetworkEvent / NetworkDirection。
本工程**不需要**自己造网络层：它已经依赖同门移植工程 fpsmatch-port 的垫片
`net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister`
（反射式：包类只需保持 encode/decode/handle 三个方法原样，字节流原样转发）。
本脚本把调用面全部改接到该垫片。

幂等：已改过的文件不再命中。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')
FPSM = os.path.join(HERE, '..', '..', 'fpsmatch-port', 'src', 'main', 'java')

PAYLOAD_CONTEXT = 'net.ptcrys.fpsmatch.common.packet.register.PayloadContext'
NPR = 'net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister'
PAYLOAD_DIRECTION = 'net.ptcrys.fpsmatch.common.packet.register.NetworkPacketRegister.PayloadDirection'


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


def discover_payload_event_import():
    """从 fpsmatch 的 FPSMatch.java 里抠出 RegisterPayloadHandlersEvent 的 import 原文。"""
    p = os.path.join(FPSM, 'net', 'ptcrys', 'fpsmatch', 'FPSMatch.java')
    for l in open(p, encoding='utf-8'):
        if 'RegisterPayloadHandlersEvent' in l and l.startswith('import '):
            return l.strip()[len('import '):-1]
    raise SystemExit('!! 未能从 fpsmatch 找到 RegisterPayloadHandlersEvent 的 import')


def java_files():
    for base, _, names in os.walk(ROOT):
        for n in names:
            if n.endswith('.java'):
                yield os.path.join(base, n)


# 发送侧：INSTANCE.send(PacketDistributor.PLAYER.with(() -> EXPR), ...) -> NetworkPacketRegister.sendToPlayer(EXPR, ...
RE_SEND_TO_PLAYER = re.compile(
    r'\b(?:[A-Za-z_][\w]*\.)*INSTANCE\s*\.\s*send\(\s*'
    r'PacketDistributor\.PLAYER\.with\(\s*\(\)\s*->\s*([^()]+?)\s*\)\s*,\s*')
# 发送侧：任意前缀 INSTANCE.sendToServer(   -> NetworkPacketRegister.sendToServer(
RE_SEND_TO_SERVER = re.compile(r'\b(?:[A-Za-z_][\w]*\.)*INSTANCE\s*\.\s*sendToServer\(')


def main():
    dry = '--dry' in sys.argv
    pe_import = discover_payload_event_import()
    print('RegisterPayloadHandlersEvent import = %s' % pe_import)

    stats = {}

    def bump(k, n=1):
        stats[k] = stats.get(k, 0) + n

    for f in sorted(java_files()):
        text = open(f, encoding='utf-8').read()
        orig = text
        rel = f.replace(ROOT + '/', '')

        # ── B0) 包类：NetworkEvent.Context -> PayloadContext ─────────────
        if 'NetworkEvent' in text:
            n = text.count('NetworkEvent.Context')
            text = text.replace('NetworkEvent.Context', 'PayloadContext')
            if n:
                bump('NetworkEvent.Context->PayloadContext', n)
            # import 行（含全限定形式）
            for old in ('import net.neoforged.neoforge.network.NetworkEvent;',):
                if old in text:
                    text = text.replace(old, 'import %s;' % PAYLOAD_CONTEXT)
                    bump('import NetworkEvent->PayloadContext')
            # 残留的全限定引用
            text, c = re.subn(r'(?<![\w.])net\.neoforged\.neoforge\.network\.NetworkEvent(?![\w])',
                              PAYLOAD_CONTEXT, text)
            if c:
                bump('net.neoforged...NetworkEvent->PayloadContext', c)

        # ── B1) BOPacketRegistration：NetworkDirection -> PayloadDirection ─
        if 'NetworkDirection' in text:
            text = text.replace('NetworkDirection.PLAY_TO_CLIENT', 'PayloadDirection.TO_CLIENT')
            text = text.replace('NetworkDirection.PLAY_TO_SERVER', 'PayloadDirection.TO_SERVER')
            text = text.replace('import net.neoforged.neoforge.network.NetworkDirection;',
                                'import %s;' % PAYLOAD_DIRECTION)
            text, c = re.subn(r'NetworkDirection(?![\w])', 'PayloadDirection', text)
            bump('NetworkDirection->PayloadDirection')

        # ── B2) 发送侧改接 ────────────────────────────────────────────
        text, c = RE_SEND_TO_PLAYER.subn(lambda m: 'NetworkPacketRegister.sendToPlayer(%s, ' % m.group(1), text)
        if c:
            bump('send(PLAYER.with)->sendToPlayer', c)
        text, c = RE_SEND_TO_SERVER.subn('NetworkPacketRegister.sendToServer(', text)
        if c:
            bump('sendToServer->NPR.sendToServer', c)

        # ── B3) 收拾 import ───────────────────────────────────────────
        if 'NetworkPacketRegister.' in text and 'import %s;' % NPR not in text:
            text = add_import(text, NPR)
            bump('+import NetworkPacketRegister')
        if 'PacketDistributor' not in text:
            before = text
            text = drop_import(text, 'net.neoforged.neoforge.network.PacketDistributor')
            if before != text:
                bump('-import PacketDistributor')

        if text != orig:
            if not dry:
                open(f, 'w', encoding='utf-8').write(text)

    # ── B4) BlockOffensive.java：主类接线（手工结构改，因为要写新方法）──
    main_java = os.path.join(ROOT, 'net', 'ptcrys', 'blockoffensive', 'BlockOffensive.java')
    text = open(main_java, encoding='utf-8').read()
    o = text

    text = drop_import(text, 'net.neoforged.neoforge.network.simple.SimpleChannel')
    text = drop_import(text, 'net.neoforged.fml.javafmlmod.FMLJavaModLoadingContext')
    text = text.replace(
        '    public static final SimpleChannel INSTANCE = PACKET_REGISTER.getChannel();\n', '')
    text = add_import(text, 'net.neoforged.fml.ModContainer')
    text = add_import(text, pe_import)

    old_ctor = '''    @SuppressWarnings("removal")
    public BlockOffensive() {
        this(FMLJavaModLoadingContext.get());
    }

    public BlockOffensive(FMLJavaModLoadingContext context) {
        IEventBus modEventBus = context.getModEventBus();
        modEventBus.addListener(this::commonSetup);'''
    new_ctor = '''    public BlockOffensive(IEventBus modEventBus, ModContainer modContainer) {
        modEventBus.addListener(this::commonSetup);
        modEventBus.addListener(this::onRegisterPackets);'''
    if old_ctor in text:
        text = text.replace(old_ctor, new_ctor)
        bump('ctor 1.21.1 签名')
    text = text.replace('context.registerConfig(', 'modContainer.registerConfig(')

    old_setup = '''    private void commonSetup(final FMLCommonSetupEvent event) {
        BOPacketRegistration.register(PACKET_REGISTER);

        event.enqueueWork(() -> {'''
    new_setup = '''    /**
     * NeoForge 1.21：网络包注册迁移到 RegisterPayloadHandlersEvent（模组总线）。
     * 注册器由事件提供，必须在注册任何包之前 bind。
     */
    private void onRegisterPackets(final RegisterPayloadHandlersEvent event) {
        PACKET_REGISTER.bind(event.registrar(BOPacketRegistration.PROTOCOL_VERSION));
        BOPacketRegistration.register(PACKET_REGISTER);
    }

    private void commonSetup(final FMLCommonSetupEvent event) {
        event.enqueueWork(() -> {'''
    if old_setup in text:
        text = text.replace(old_setup, new_setup)
        bump('onRegisterPackets 新增')

    if text != o:
        if not dry:
            open(main_java, 'w', encoding='utf-8').write(text)
        bump('BlockOffensive.java 主接线')

    print('== fix_b 命中 ==')
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print('  %-45s %d' % (k, v))


if __name__ == '__main__':
    main()
