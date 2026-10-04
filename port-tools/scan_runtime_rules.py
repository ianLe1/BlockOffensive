#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeoForge 1.21.1 运行期严格性扫描（规则 2 / 3 / 4 + 显式注册变体）。

规则 1（@SubscribeEvent 参数必须是该总线的事件）由同目录的 scan_bus.py 负责（要递归 javap）。

规则 2：@EventBusSubscriber 的类自身必须至少有一个 @SubscribeEvent 方法。
        IllegalArgumentException: class X has no @SubscribeEvent methods, but register was called anyway
规则 3：被注册为监听器的类，其父类（递归）不允许带 @SubscribeEvent 方法。
        IllegalArgumentException: Attempting to register a listener object of type X,
        however its supertype Y has a @SubscribeEvent method ... This is not allowed!
规则 4：@EventBusSubscriber 走静态注入路径，该类每个 @SubscribeEvent 方法都必须是 static。
        IllegalArgumentException: Method X.m(...) annotated with @SubscribeEvent is not static

附加：显式 NeoForge.EVENT_BUS.register(X.class) 也要求 static；
      register(obj) / register(this) 允许实例方法，但父类仍受规则 3 约束。
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else 'src/main/java'
SRC = ROOT


def strip(t):
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    t = re.sub(r'//[^\n]*', '', t)
    return t


def methods_with_annotation(text, anno):
    """返回 [(声明串(含修饰符+返回类型), 方法名)]：紧跟 @anno 之后的方法声明。

    注意不要用「一个大 `(?:...)*` 重复组去吞修饰符」——那样 group 只会保留最后一次重复，
    修饰符会全部漏进返回类型组，于是 `'static' in mods` 永远为假（本脚本踩过这个坑）。
    正确做法：先定位注解结尾，再从其后的 400 字符里一次性 match 出「注解* + 声明 + 方法名 (」。
    """
    out = []
    for m in re.finditer(r'@' + anno + r'(?:\([^)]*\))?', text):
        tail = text[m.end():m.end() + 400]
        sig = re.match(r'(?:\s*@[\w.]+(?:\([^)]*\))?)*\s*([^;{]*?)\s+(\w+)\s*\(', tail, re.S)
        if not sig:
            continue
        out.append((' '.join(sig.group(1).split()), sig.group(2)))
    return out


# ---------- 采集 ----------
types = {}       # fq -> dict
by_simple = {}   # simple -> fq (可能重名，记第一个)
for base, _, names in os.walk(SRC):
    for n in names:
        if not n.endswith('.java'):
            continue
        f = os.path.join(base, n)
        raw = strip(open(f, encoding='utf-8').read())
        pkg = re.search(r'^package\s+([\w.]+);', raw, re.M)
        if not pkg:
            continue
        pkg = pkg.group(1)
        for tm in re.finditer(
                r'(?:^|\n)((?:[ \t]*@[\w.]+(?:\([^)]*\))?[ \t]*\n)*)'
                r'[ \t]*(?:(?:public|final|abstract|sealed|non-sealed|static)\s+)*'
                r'(class|interface|enum|record)\s+(\w+)'
                r'((?:\s+extends\s+[\w.$<>,\s]+?)?)'
                r'((?:\s+implements\s+[\w.$<>,\s]+?)?)\s*\{', raw):
            annos, kind, name, ext, impl = tm.groups()
            fq = pkg + '.' + name
            # 该类型体的范围：从 { 到文件结束（粗略）；用一个宽松窗口统计注解
            body = raw[tm.end():]
            extm = re.search(r'extends\s+([\w.]+)', ext or '')
            types[fq] = {
                'file': f,
                'name': name,
                'kind': kind,
                'extends': extm.group(1) if extm else None,
                'eventbus': '@EventBusSubscriber' in annos,
                'eb_bus': (re.search(r'@EventBusSubscriber\(([^)]*)\)', annos) or [None, ''])[1] or '',
                'subs': methods_with_annotation(body, 'SubscribeEvent'),
            }
            by_simple.setdefault(name, fq)

# 显式注册：NeoForge.EVENT_BUS.register(X.class) / register(new X()) / register(this) / register(obj)
static_required = set()
obj_registered = set()
for fq, t in types.items():
    raw = open(t['file'], encoding='utf-8').read()
    for m in re.finditer(r'\.register\(\s*([\w.$]+)\.class\s*\)', raw):
        static_required.add(m.group(1))
    for m in re.finditer(r'\.register\(\s*new\s+([\w.$]+)\s*\(', raw):
        obj_registered.add(m.group(1))
    if re.search(r'\.register\(\s*this\s*\)', raw):
        obj_registered.add(t['name'])

problems = 0


def report(rule, msg):
    global problems
    problems += 1
    print('!! [规则 %s] %s' % (rule, msg))


# ---------- 规则 2 / 4 ----------
for fq, t in sorted(types.items()):
    if t['eventbus']:
        if not t['subs']:
            report(2, '%s 带 @EventBusSubscriber 但没有任何 @SubscribeEvent' % fq)
        for mods, name in t['subs']:
            if 'static' not in mods.split():
                report(4, '%s#%s 带 @EventBusSubscriber，但 @SubscribeEvent 方法不是 static（mods=%r）'
                       % (fq, name, mods.strip()))
    else:
        # 显式 register(X.class) 的类同样要求 static
        if t['name'] in static_required:
            for mods, name in t['subs']:
                if 'static' not in mods.split():
                    report(4, '%s#%s 由 EVENT_BUS.register(X.class) 注册，@SubscribeEvent 必须是 static（mods=%r）'
                           % (fq, name, mods.strip()))
            if not t['subs']:
                report(2, '%s 由 EVENT_BUS.register(X.class) 注册，但没有任何 @SubscribeEvent' % fq)

# ---------- 规则 3 ----------
reg_names = set()
for fq, t in types.items():
    if t['eventbus']:
        reg_names.add(t['name'])
reg_names |= static_required | obj_registered

for fq, t in sorted(types.items()):
    if t['name'] not in reg_names:
        continue
    cur = t['extends']
    chain = []
    seen = set()
    while cur and cur not in seen and len(chain) < 12:
        seen.add(cur)
        pfq = by_simple.get(cur)
        if not pfq:
            chain.append(cur + '(外部/未知)')
            break
        p = types[pfq]
        if p['subs']:
            report(3, '%s 被注册为监听器，但其父类 %s 有 @SubscribeEvent 方法：%s'
                   % (fq, pfq, ', '.join(n for _, n in p['subs'])))
            break
        chain.append(cur)
        cur = p['extends']

print()
print('扫描目录 %s：%d 个类型，%d 处违规' % (SRC, len(types), problems))
