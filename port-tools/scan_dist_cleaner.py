#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeoForge 1.21.1 运行期规则 6 扫描：带 @EventBusSubscriber 的类，其**顶层声明方法/字段的签名**
不得引用客户端类。

为什么：`AutomaticEventSubscriber.inject` 会对每个被标注的类调 `Class#getDeclaredMethods()`，
JVM 为了构造 `Method` 对象必须解析**每个声明方法的参数/返回类型**。在 DEDICATED_SERVER 下
`RuntimeDistCleaner` 对 `net.minecraft.client.*` 直接抛：

    java.lang.RuntimeException: Attempted to load class net/minecraft/client/Minecraft
    for invalid dist DEDICATED_SERVER
      at ...RuntimeDistCleaner.processClassWithFlags(RuntimeDistCleaner.java:60)
      at ...AutomaticEventSubscriber.lambda$inject$4(AutomaticEventSubscriber.java:60)

**方法体里**用客户端类是安全的（那只在客户端被调用时才会解析），只有**签名**致命。

本项目实例：`blockoffensive-port/src/main/java/net/ptcrys/blockoffensive/item/CompositionC4.java:208`
`private void disableMovementKeys(Minecraft mc)` —— 改成 `private void disableMovementKeys()`
并在方法体内 `Minecraft mc = Minecraft.getInstance();` 即可。

注意区分**匿名内部类**：`new IClientItemExtensions() { ... }` 里的方法属于 `Outer$1`，不是外部类的
声明方法，不受影响。所以本脚本按大括号深度只取**深度 1**（类体直接层）的方法/字段。

用法：python3 tools/scan_dist_cleaner.py [src/main/java]
"""
import os
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'src/main/java'

CLIENT_PKG = ('net.minecraft.client.', 'com.mojang.blaze3d.', 'net.neoforged.neoforge.client.',
              'icyllis.modernui.')


def scan_file(path):
    text = open(path, encoding='utf-8').read()
    if '@EventBusSubscriber' not in text:
        return []
    # 只在专用服务端**会被处理**的类才致命：注解里带 value = Dist.CLIENT 的类
    # NeoForge 在服务端根本不会去读它的方法（FPSMatch 的 11 处假阳性就是这么来的）。
    for m in re.finditer(r'@EventBusSubscriber(?:\(([^)]*)\))?', text):
        if m.group(1) and 'Dist.CLIENT' in m.group(1):
            return []
    # import 表：简单名 -> 全限定名
    imports = {}
    for m in re.finditer(r'^import\s+(?:static\s+)?([\w.$]+);', text, re.M):
        full = m.group(1)
        imports[full.rsplit('.', 1)[-1]] = full
    # 包内自有类不算（本仓库自己的类名不会被 dist cleaner 拒）
    simple = {}
    for n, f in imports.items():
        if f.startswith(CLIENT_PKG):
            simple[n] = f

    lines = text.split('\n')
    depth = 0
    bad = []
    for i, ln in enumerate(lines, 1):
        stripped = ln.strip()
        # 先判断本行（在归属深度 = 1 时）是不是声明
        if depth == 1 and not stripped.startswith(('//', '*', '/*', '@')):
            m = re.match(r'^(?:public|protected|private|static|final|abstract|synchronized|native|'
                         r'default|transient|volatile|\s)*([\w.$]+(?:\s*<[^{;=]*>)?(?:\s*\[\s*\])*)\s+'
                         r'(\w+)\s*(\(|;|=|,)', stripped)
            if m:
                ret, name, tail = m.group(1), m.group(2), m.group(3)
                types = [ret.strip()]
                if tail == '(':
                    cp = stripped.find('(', m.start(3))
                    depth_p = 0
                    j = cp
                    while j < len(stripped):
                        if stripped[j] == '(':
                            depth_p += 1
                        elif stripped[j] == ')':
                            depth_p -= 1
                            if depth_p == 0:
                                break
                        j += 1
                    params = stripped[cp + 1:j]
                    for p in params.split(','):
                        p = p.strip()
                        if not p:
                            continue
                        p = re.sub(r'^(@\w+(\([^)]*\))?\s*)+', '', p)
                        p = re.sub(r'^(final\s+)+', '', p)
                        types.append(p.split('=')[0].strip().rsplit(' ', 1)[0].strip())
                for t in types:
                    base = re.sub(r'<.*', '', t).replace('[]', '').strip()
                    base = base.rsplit('.', 1)[-1]
                    if base in simple:
                        bad.append((i, name, t.strip(), simple[base]))
        depth += ln.count('{') - ln.count('}')
    return bad


total = 0
for base, _, names in os.walk(SRC):
    for n in sorted(names):
        if not n.endswith('.java'):
            continue
        f = os.path.join(base, n)
        for lineno, meth, typ, full in scan_file(f):
            total += 1
            print('!! %s:%d\n   方法/字段 %s 的签名里出现客户端类型 %s（%s）'
                  % (f.replace(SRC + '/', ''), lineno, meth, typ, full))
print('\n规则 6：共 %d 处' % total)
