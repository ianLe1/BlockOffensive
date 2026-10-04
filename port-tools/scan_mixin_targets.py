#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeoForge 1.21.1 运行期规则 5 扫描：mixin 的 @At(target = "L<owner>;<name><desc>") 是否仍存在。

为什么需要：mixin 的 target 串是**字符串**，编译期完全不校验。1.20.1→1.21.1 里被改名/删除的
方法（如 Entity#setSecondsOnFire(int) → igniteForSeconds(float)）只会在目标类**运行期加载**时
才炸，报错形如：

    InjectionError: Critical injection failure: Callback method ... failed injection check,
    (0/1) succeeded. Scanned 0 target(s). No refMap loaded.

本项目踩到的实例：`mixin/compat/lrt/LrtSplashFireStatsMixin`（target 写在
`Lnet/minecraft/world/entity/LivingEntity;setSecondsOnFire(I)V`）与 `LrtCloudFireStatsMixin`
（`Entity;setSecondsOnFire(I)V`），而 LRT 1.21.1 的字节码实际调用的是
`net/minecraft/world/entity/{LivingEntity,Entity}.igniteForSeconds:(F)V`。

做法：抓出所有 target 串，用 `javap -p -s`（会同时打印 JVM descriptor）在类路径里核对
「方法名 + descriptor」是否存在。descriptor 直接字符串比对，不做类型名翻译。

用法：python3 tools/scan_mixin_targets.py [src/main/java]
"""
import os
import re
import subprocess
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'src/main/java'
HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
GH = os.path.join(PROJ, '.gradle-home')

CP = [os.path.join(PROJ, 'libs', j) for j in sorted(os.listdir(os.path.join(PROJ, 'libs')))
      if j.endswith('.jar')]
for pat in ('caches/neoformruntime/intermediate_results',
            'caches/modules-2/files-2.1/net.neoforged/neoforge',
            'caches/modules-2/files-2.1/net.neoforged/bus',
            'caches/modules-2/files-2.1/net.neoforged.fancymodloader'):
    root = os.path.join(GH, pat)
    if os.path.isdir(root):
        for b, _, ns in os.walk(root):
            for n in ns:
                if n.endswith('.jar'):
                    CP.append(os.path.join(b, n))
CPSTR = os.pathsep.join(CP)

_cache = {}


def javap(cls):
    if cls in _cache:
        return _cache[cls]
    try:
        out = subprocess.run(['javap', '-p', '-s', '-cp', CPSTR, cls],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception as e:                                    # noqa: BLE001
        out = ''
    _cache[cls] = out
    return out


def _has(txt, name, desc):
    lines = txt.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip() != 'descriptor: ' + desc or i == 0:
            continue
        prev = lines[i - 1]
        if '(' in desc and name + '(' in prev:
            return True
        if '(' not in desc and re.search(r'\b' + re.escape(name) + r'\b', prev):
            return True
    return False


def check(owner, name, desc):
    """owner 内部名(a/b/C)，name 方法名，desc 形如 (I)V 或字段类型 I。

    注意：INVOKE 的 target owner 是**调用点静态类型**，可以是实际声明该方法的类的子类
    （final 方法尤其常见：1.21.1 的 igniteForSeconds 只声明在 Entity 上，而 LRT 的字节码
    以 LivingEntity 为 owner 调用它）。所以找不到时要沿 superclass 链上溯。
    """
    cls = owner.replace('/', '.')
    seen = set()
    while cls and cls not in seen:
        seen.add(cls)
        txt = javap(cls)
        if not txt:
            return 'owner 类找不到'
        if _has(txt, name, desc):
            return None
        m = re.search(r'^\s*(?:public |private |protected )?(?:final )?(?:abstract )?'
                      r'(?:class|interface|enum|record)\s+[\w.$]+\s+extends\s+([\w.$]+)', txt, re.M)
        cls = m.group(1) if m else None
    return '方法/字段不存在（含父类链）'


targets = []
pat = re.compile(r'target\s*=\s*"(L([^;]+);([^(\s]+)(\([^)]*\)[^"\s]+|:[^"\s]+))"')
for base, _, names in os.walk(SRC):
    for n in names:
        if not n.endswith('.java'):
            continue
        f = os.path.join(base, n)
        for m in pat.finditer(open(f, encoding='utf-8').read()):
            targets.append((f, m.group(1), m.group(2), m.group(3), m.group(4)))

print('共 %d 条 mixin target' % len(targets))
bad = 0
for f, whole, owner, name, tail in targets:
    if tail.startswith(':'):
        desc = tail[1:]
    else:
        i = tail.rindex(')')
        desc = tail[:i + 1] + tail[i + 1:]
    why = check(owner, name, desc)
    if why:
        bad += 1
        print('!! %s\n   %s -> %s   [%s]' % (f.replace(SRC + '/', ''), whole, why, name))
print('\n%d 条可疑（%d/%d）' % (bad, bad, len(targets)))
