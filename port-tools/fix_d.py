#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 D：裁剪三个「兼容层」及其调用点。

裁剪依据（不是偷懒，是与运行时事实对齐）：这三个兼容层编译期就依赖三个**不在本整合包内**的模组，
上游的调用点全部裹在 `BOImpl.isXxxLoaded()` / `FPSMImpl.findXxxMod()` 守卫里，运行时判定恒为假。
所以「删掉兼容类 + 把守卫分支变成空」= 精确模拟「模组未安装」，而不是删功能。

  1) PhysicsMod  → net.diebuddies.* / physx.*       （上游 dependencies.gradle: modImplementation physicsmod）
  2) HitIndication → com.rosymaple.hitindication.*  （上游: modImplementation hit-indication）
  3) CS Grenade  → club.pisquad.minecraft.csgrenades.*（上游: modImplementation counterstrikegrenade）

幂等：所有替换都做命中数断言，重复运行会报「期望 N 实际 0」而不是静默改坏。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'src', 'main', 'java')
P = os.path.join(SRC, 'net', 'ptcrys', 'blockoffensive')
DRY = '--dry' in sys.argv

DELETE = [
    'compat/PhysicsModCompat.java',
    'compat/HitIndicationCompat.java',
    'compat/CSGrenadeCompat.java',
    'net/PxDeathCompatS2CPacket.java',
    'net/PxRagdollRemovalCompatS2CPacket.java',
    'command/BOPhysicsRagdollDebugCommand.java',
]

log = []
fails = []


def rd(rel):
    return open(os.path.join(P, rel), encoding='utf-8').read()


def wr(rel, t):
    if not DRY:
        open(os.path.join(P, rel), 'w', encoding='utf-8').write(t)


def sub(rel, pattern, repl, expected=1, flags=0):
    t = rd(rel)
    t2, n = re.subn(pattern, repl, t, flags=flags)
    if n != expected:
        fails.append('%-34s 期望 %d 命中，实际 %d  ← %s' % (rel, expected, n, pattern[:64]))
        return
    wr(rel, t2)
    log.append('%-34s x%d  %s' % (rel, n, pattern[:52].replace('\n', '\\n')))


# ── 1) 删文件 ───────────────────────────────────────────────────────────

def _already_applied():
    """幂等门禁：裁剪确已完成时整体跳过（避免重跑时刷出一堆「期望 N 实际 0」断言失败）。"""
    gone = all(not os.path.exists(os.path.join(P, rel)) for rel in DELETE)
    if not gone:
        return False
    try:
        menu = rd('compat/BOMenuIntegration.java')
        reg = rd('net/BOPacketRegistration.java')
        core = rd('BlockOffensive.java')
    except OSError:
        return False
    return ('registerExtensionPoint(IConfigScreenFactory.class' in menu
            and 'PxDeathCompatS2CPacket.class' not in reg
            and 'PhysicsModCompat' not in core
            and 'CSGrenadeCompat' not in core)


if _already_applied():
    print('== fix_d 执行 ==')
    print('  已全部应用，跳过（幂等门禁）')
    sys.exit(0)

for rel in DELETE:
    p = os.path.join(P, rel)
    if os.path.exists(p):
        if not DRY:
            os.remove(p)
        log.append('删除 %s' % rel)
    else:
        fails.append('删除 %s：文件不存在（可能已裁过）' % rel)

# ── 2) BlockOffensive.registerCompat：两个兼容分支改空 ─────────────────
sub('BlockOffensive.java', r'import net\.ptcrys\.blockoffensive\.compat\.CSGrenadeCompat;\n', '')
sub('BlockOffensive.java', r'import net\.ptcrys\.blockoffensive\.compat\.PhysicsModCompat;\n', '')
sub('BlockOffensive.java',
    r'    private static void registerCompat\(\) \{\n(?:.*?\n)*?    \}\n',
    '    private static void registerCompat() {\n'
    '        // 1.21.1 移植：PhysicsMod / CS Grenade / HitIndication 兼容层已裁剪，\n'
    '        // 依赖模组不在本整合包内（上游调用点原本就裹在 isXxxLoaded() 守卫里）。见 PORT-NOTES.md。\n'
    '    }\n')

# ── 3) CSDeathMessageHud：CS Grenade 击杀图标注册 ──────────────────────
sub('client/screen/hud/CSDeathMessageHud.java',
    r'import net\.ptcrys\.blockoffensive\.compat\.CSGrenadeCompat;\n', '')
sub('client/screen/hud/CSDeathMessageHud.java',
    r'\n        if \(BOImpl\.isCounterStrikeGrenadesLoaded\(\)\) \{\n'
    r'            CSGrenadeCompat\.registerKillIcon\(itemToIcon\);\n        \}\n', '\n')

# ── 4) CSMap：实体清理判定 + 两个 physics 发包方法改空壳 ────────────────
sub('map/CSMap.java', r'import net\.ptcrys\.blockoffensive\.compat\.CSGrenadeCompat;\n', '')
sub('map/CSMap.java', r'import net\.ptcrys\.blockoffensive\.net\.PxDeathCompatS2CPacket;\n', '')
sub('map/CSMap.java', r'import net\.ptcrys\.blockoffensive\.net\.PxRagdollRemovalCompatS2CPacket;\n', '')
sub('map/CSMap.java', r' \|\| \(FPSMImpl\.findCounterStrikeGrenadesMod\(\) && CSGrenadeCompat\.is\(entity\)\)', '')
sub('map/CSMap.java',
    r'    public void sendPhysicsRagdollRemovalPacket\(UUID uuid\) \{\n(?:.*?\n)*?    \}\n',
    '    public void sendPhysicsRagdollRemovalPacket(UUID uuid) {\n'
    '        // 1.21.1 移植：PhysicsMod 兼容层已裁剪，见 PORT-NOTES.md。\n'
    '    }\n')
sub('map/CSMap.java',
    r'    protected void sendPhysicsDeathPacket\(ServerPlayer deadPlayer\) \{\n(?:.*?\n)*?    \}\n',
    '    protected void sendPhysicsDeathPacket(ServerPlayer deadPlayer) {\n'
    '        // 1.21.1 移植：PhysicsMod 兼容层已裁剪，见 PORT-NOTES.md。\n'
    '    }\n')

# ── 5) CSGameMap：物理 ragdoll 清理调用点 ───────────────────────────────
sub('map/CSGameMap.java',
    r'import net\.ptcrys\.blockoffensive\.net\.PxRagdollRemovalCompatS2CPacket;\n', '')
sub('map/CSGameMap.java',
    r'\n        sendPhysicsRagdollRemovalPacket\(PxRagdollRemovalCompatS2CPacket\.ALL\);\n', '\n')

# ── 6) CSGameHud：HitIndication 渲染调用点 ─────────────────────────────
sub('client/screen/hud/CSGameHud.java',
    r'import net\.ptcrys\.blockoffensive\.compat\.HitIndicationCompat;\n', '')
sub('client/screen/hud/CSGameHud.java',
    r'        if \(BOImpl\.isHitIndicationLoaded\(\)\) \{\n'
    r'            HitIndicationCompat\.Renderer\.render\(gui\.getMinecraft\(\)\.getWindow\(\), guiGraphics\);\n'
    r'        \}\n', '')
sub('client/screen/hud/CSGameHud.java', r'\n        syncSpectatorMode\(false\);', '\n        syncSpectatorMode(false);')

# ── 7) BOPacketRegistration：删掉两个 Px 包（都在索引 9 之后，不影响 2/6/9 方向表）──
sub('net/BOPacketRegistration.java', r'                PxDeathCompatS2CPacket\.class,\n', '')
sub('net/BOPacketRegistration.java', r'                PxRagdollRemovalCompatS2CPacket\.class,\n', '')
# （Px 包与 BOPacketRegistration 同包，不需要 import 行）

# ── 8) BOCommandRegister：物理 ragdoll 调试命令的挂载点 ─────────────────
sub('command/BOCommandRegister.java',
    r'            event\.addChild\(BOPhysicsRagdollDebugCommand\.fpsmCommand\(\)\);\n', '')
sub('command/BOCommandRegister.java',
    r'                    \.then\(BOPhysicsRagdollDebugCommand\.fpsmCommand\(\)\)\n', '')

# ── 9) BOMenuIntegration：ConfigScreenHandler → IConfigScreenFactory（活代码修复）──
sub('compat/BOMenuIntegration.java',
    r'import net\.neoforged\.neoforge\.client\.ConfigScreenHandler;\n',
    'import net.neoforged.neoforge.client.gui.IConfigScreenFactory;\n')
sub('compat/BOMenuIntegration.java',
    r'import net\.neoforged\.fml\.ModLoadingContext;\n',
    'import net.neoforged.fml.ModList;\n')
sub('compat/BOMenuIntegration.java',
    r'    @SuppressWarnings\("removal"\)\n    public static void registerModsPage\(\) \{\n'
    r'        ModLoadingContext\.get\(\)\.registerExtensionPoint\(ConfigScreenHandler\.ConfigScreenFactory\.class, '
    r'\(\) -> new ConfigScreenHandler\.ConfigScreenFactory\(\(client, parent\) -> getConfigScreen\(parent\)\)\);\n'
    r'    \}\n',
    '    public static void registerModsPage() {\n'
    '        ModList.get().getModContainerById("blockoffensive").ifPresent(container -> {\n'
    '            IConfigScreenFactory factory = (mod, parent) -> getConfigScreen(parent);\n'
    '            container.registerExtensionPoint(IConfigScreenFactory.class, factory);\n'
    '        });\n'
    '    }\n')

print('== fix_d 执行 ==')
for l in log:
    print('  ' + l)
if fails:
    print('== 断言失败（需人工处理）==')
    for f in fails:
        print('  !! ' + f)
    sys.exit(1)
