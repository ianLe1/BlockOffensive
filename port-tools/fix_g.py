#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 G：GUI/HUD 层

1.21.1 事实（javap 实证，见 PORT-NOTES.md）：
  * `net.neoforged.neoforge.client.gui.overlay.{ForgeGui,VanillaGuiOverlay}` 整个包不存在；
    GUI 改为 LayeredDraw 分层：`net.neoforged.neoforge.client.gui.VanillaGuiLayers`（一堆 ResourceLocation）
    + `RenderGuiLayerEvent.Pre/Post`（`getName(): ResourceLocation`、`getGuiGraphics()`、`getPartialTick()`，
    Pre 实现 ICancellableEvent）+ `RegisterGuiLayersEvent`。
  * `IHudRenderer`（由 fpsmatch-port 提供，BO 直接实现它）在 1.21.1 是：
      void onRenderGuiLayerPre(RenderGuiLayerEvent.Pre event);
      void onSpectatorRender(GuiGraphics, DeltaTracker);
      void onPlayerRender(GuiGraphics, DeltaTracker);
    ⇒ 上游的 `(ForgeGui gui, GuiGraphics, float partialTick, int w, int h)` 要改成两参，
       w/h 从 `guiGraphics.guiWidth()/guiHeight()` 取。
  * `ForgeGui gui` 在 BO 的这些方法里**从未被使用**（只当参数传来传去）⇒ 直接删参数。
  * 顶点 API：`Tesselator.getBuilder()` 与 `BufferBuilder.begin(...)`/`.endVertex()`/`Tesselator.end()` 全删；
    新写法 = `BufferBuilder b = Tesselator.getInstance().begin(Mode, VertexFormat)` +
    `b.addVertex(Matrix4f,x,y,z).setColor(r,g,b,a)` + `BufferUploader.drawWithShader(b.buildOrThrow())`。
幂等。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')
STATS = []


def bump(k, n):
    STATS.append('%-58s %d' % (k, n))


def sub(text, old, new, label, expect=None, required=True):
    c = text.count(old)
    if c == 0:
        if required:
            raise SystemExit('未命中（应为 %s）：%s' % (expect, label))
        return text, 0
    if expect is not None and c != expect:
        raise SystemExit('命中数不符：%s 期望 %s 实际 %d' % (label, expect, c))
    bump(label, c)
    return text.replace(old, new), c


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


GUI_IMPORTS = [
    ('import net.neoforged.neoforge.client.event.RenderGuiOverlayEvent;',
     'import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;'),
    ('import net.neoforged.neoforge.client.gui.overlay.ForgeGui;\n', ''),
    ('import net.neoforged.neoforge.client.gui.overlay.VanillaGuiOverlay;',
     'import net.neoforged.neoforge.client.gui.VanillaGuiLayers;'),
]


def apply_gui_imports(text, rel):
    """三个 GUI import 的改写（文件里没有的那条跳过）。"""
    for a, b in GUI_IMPORTS:
        text, c = sub(text, a, b, '%s: import %s' % (rel, a.split('.')[-1][:40]), required=False)
    return text


def overlay_body(text):
    """VanillaGuiOverlay 比较 -> VanillaGuiLayers 比较。"""
    n = 0
    text, c = re.subn(r'(\w+)\.getOverlay\(\) == VanillaGuiOverlay\.(\w+)\.type\(\)',
                      r'\1.getName().equals(VanillaGuiLayers.\2)', text)
    n += c
    text, c = re.subn(r'(\w+)\.getOverlay\(\)\.id\(\)\.getPath\(\)',
                      r'\1.getName().getPath()', text)
    n += c
    text, c = re.subn(r'(\w+)\.getOverlay\(\)\.id\(\)', r'\1.getName()', text)
    n += c
    text, c = re.subn(r'(\w+)\.getOverlay\(\) != VanillaGuiOverlay\.(\w+)\.type\(\)',
                      r'!\1.getName().equals(VanillaGuiLayers.\2)', text)
    n += c
    return text, n



def _already_applied():
    """幂等门禁：本脚本的全部改动都已落地时整体跳过（部分落地则仍走断言路径报错）。"""
    checks = [
        ('client/screen/hud/CSGameHud.java', 'VanillaGuiLayers'),
        ('client/screen/hud/CSGameHud.java', 'onRenderGuiLayerPre'),
        ('client/screen/hud/CSMvpHud.java', 'Tesselator.getInstance().begin('),
        ('client/BOClientEvent.java', 'RenderGuiLayerEvent.Post'),
        ('client/shop/ShopPresentationEvents.java', 'VanillaGuiLayers'),
        ('client/screen/hud/animation/KillAnimator.java', 'GuiGraphics guiGraphics, int centerX, int y'),
    ]
    for rel, marker in checks:
        p = os.path.join(ROOT, 'net/ptcrys/blockoffensive', rel)
        if marker not in open(p, encoding='utf-8').read():
            return False
    return True


def main():
    dry = '--dry' in sys.argv
    changed = []
    if _already_applied():
        print('== fix_g 命中 ==\n  已全部应用，跳过（幂等门禁）')
        return

    def handle(rel_suffix, fn):
        for base, _, names in os.walk(ROOT):
            for name in names:
                p = os.path.join(base, name)
                rel = p.replace(ROOT + '/', '')
                if not rel.endswith(rel_suffix):
                    continue
                text = orig = open(p, encoding='utf-8').read()
                text = fn(text, rel)
                if text != orig:
                    changed.append(rel)
                    if not dry:
                        open(p, 'w', encoding='utf-8').write(text)
                return
        raise SystemExit('找不到文件 ' + rel_suffix)

    # ── 1) CSGameHud ────────────────────────────────────────────────
    def cs_game_hud(text, rel):
        text = apply_gui_imports(text, rel)
        text = add_import(text, 'net.minecraft.client.DeltaTracker')

        for which, spec in (('onSpectatorRender', 'true'), ('onPlayerRender', 'false')):
            old = ('public void %s(ForgeGui gui, GuiGraphics guiGraphics, float partialTick, '
                   'int screenWidth, int screenHeight) {' % which)
            new = ('public void %s(GuiGraphics guiGraphics, DeltaTracker deltaTracker) {\n'
                   '        int screenWidth = guiGraphics.guiWidth();\n'
                   '        int screenHeight = guiGraphics.guiHeight();' % which)
            text, _ = sub(text, old, new, '%s: %s 签名+尺寸来源' % (rel, which), expect=1)

        text, c = sub(text, 'ForgeGui gui, ', '', '%s: 单行签名去 ForgeGui' % rel, required=False)
        text, c2 = re.subn(r'\n\s*ForgeGui gui,', '', text)
        bump('%s: 多行签名去 ForgeGui' % rel, c2)
        text, c3 = re.subn(r', gui(?=[,)])', '', text)
        bump('%s: 调用点去 gui 实参' % rel, c3)

        text, _ = sub(text, 'public void onRenderGuiOverlayPre(RenderGuiOverlayEvent.Pre event) {',
                      'public void onRenderGuiLayerPre(RenderGuiLayerEvent.Pre event) {',
                      '%s: onRenderGuiOverlayPre -> onRenderGuiLayerPre' % rel, expect=1)
        text, n = overlay_body(text)
        bump('%s: overlay 比较改写' % rel, n)
        return text

    # ── 2) 动画器 ───────────────────────────────────────────────────
    def animator(text, rel):
        text, _ = sub(text, 'import net.neoforged.neoforge.client.gui.overlay.ForgeGui;\n', '',
                      '%s: 删 ForgeGui import' % rel)
        text, _ = sub(text, 'ForgeGui gui, ', '', '%s: 去 ForgeGui 参数' % rel, expect=1)
        return text

    # ── 3) BOClientEvent / ShopPresentationEvents ───────────────────
    def client_event(text, rel):
        text = apply_gui_imports(text, rel)
        text, _ = sub(text, 'onRenderGuiOverlayPost(RenderGuiOverlayEvent.Post event)',
                      'onRenderGuiLayerPost(RenderGuiLayerEvent.Post event)',
                      '%s: onRenderGuiOverlayPost -> onRenderGuiLayerPost' % rel, expect=1)
        text, n = overlay_body(text)
        bump('%s: overlay 比较改写' % rel, n)
        return text

    def shop_events(text, rel):
        text, _ = sub(text, 'import net.neoforged.neoforge.client.event.RenderGuiOverlayEvent;',
                      'import net.neoforged.neoforge.client.event.RenderGuiLayerEvent;',
                      '%s: RenderGuiOverlayEvent -> RenderGuiLayerEvent' % rel)
        text, _ = sub(text, 'import net.neoforged.neoforge.client.gui.overlay.VanillaGuiOverlay;',
                      'import net.neoforged.neoforge.client.gui.VanillaGuiLayers;',
                      '%s: VanillaGuiOverlay -> VanillaGuiLayers' % rel)
        text, _ = sub(text, 'hideCrosshair(RenderGuiOverlayEvent.Pre event)',
                      'hideCrosshair(RenderGuiLayerEvent.Pre event)',
                      '%s: hideCrosshair 签名' % rel, expect=1)
        text, n = overlay_body(text)
        bump('%s: overlay 比较改写' % rel, n)
        return text

    # ── 4) CSMvpHud 顶点 API ────────────────────────────────────────
    def mvp_hud(text, rel):
        text, c = sub(text, '        Tesselator tesselator = Tesselator.getInstance();\n'
                            '        BufferBuilder buffer = tesselator.getBuilder();\n', '',
                      '%s: 删 getBuilder 两行' % rel, required=False)
        text, n = re.subn(r'buffer\.begin\((VertexFormat\.Mode\.\w+), (DefaultVertexFormat\.\w+)\);',
                          r'BufferBuilder buffer = Tesselator.getInstance().begin(\1, \2);', text)
        bump('%s: buffer.begin -> Tesselator.begin' % rel, n)
        text, n = re.subn(r'buffer\.vertex\(', 'buffer.addVertex(', text)
        bump('%s: vertex -> addVertex' % rel, n)
        text, n = re.subn(r'\.color\(([^()]*)\)\.endVertex\(\);', r'.setColor(\1);', text)
        bump('%s: color+endVertex -> setColor' % rel, n)
        text, n = re.subn(r'tesselator\.end\(\);', 'BufferUploader.drawWithShader(buffer.buildOrThrow());', text)
        bump('%s: tesselator.end -> BufferUploader' % rel, n)
        if n:
            text = add_import(text, 'com.mojang.blaze3d.vertex.BufferUploader')
        return text

    handle('client/screen/hud/CSGameHud.java', cs_game_hud)
    handle('client/screen/hud/animation/KillAnimator.java', animator)
    handle('client/screen/hud/animation/EnderKillAnimator.java', animator)
    handle('client/BOClientEvent.java', client_event)
    handle('client/shop/ShopPresentationEvents.java', shop_events)
    handle('client/screen/hud/CSMvpHud.java', mvp_hud)

    print('== fix_g 命中 ==')
    for s in STATS:
        print('  ' + s)
    print('  涉及文件 %d 个' % len(changed))
    for c in changed:
        print('    ' + c)


if __name__ == '__main__':
    main()
