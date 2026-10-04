#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描 @SubscribeEvent 方法的参数类型，判定它属于哪条总线（game / mod），
再比对类级 @EventBusSubscriber 声明的总线 / 手工模组注册入口，找出不匹配。

NeoForge 1.21.1 的 IEventBus.register(Object) 会逐个校验 @SubscribeEvent 的参数类型
必须属于该总线；把 mod 总线事件（IModBusEvent）挂到 game 总线会直接抛
IllegalArgumentException 并让服务端 Failed to start。
上游是 1.20.1 Forge，没这个校验，所以这类错误只在 1.21.1 才暴露。
"""
import os
import re
import subprocess
import glob
import json

ROOT = 'src/main/java'

CP = ':'.join(
    ['.gradle-home/caches/modules-2/files-2.1/net.neoforged.fancymodloader/loader/4.0.45/4a0968c2ec6234d58e0a9ed97acafc08cc8f33b5/loader-4.0.45.jar',
     '.gradle-home/caches/modules-2/files-2.1/net.neoforged/bus/8.0.5/4a0968c2ec6234d58e0a9ed97acafc08cc8f33b5/bus-8.0.5.jar',
     '.gradle-home/caches/modules-2/files-2.1/net.neoforged/neoforge/21.1.253/37f196cd52e85a3bb5d48f40f8b7d13c29a00ecb/neoforge-21.1.253-universal.jar',
     '.gradle-home/caches/neoformruntime/intermediate_results/compiledWithNeoForge_a0046ebdf41f634b0b890c000fcb8b87f4d1d9fd_output.jar',
     ] + glob.glob('libs/*.jar'))

# 补上 bus jar 的真实路径（上面的哈希是占位，实际用 glob 兜底）
extra = glob.glob('.gradle-home/caches/modules-2/files-2.1/net.neoforged/bus/*/*/bus-*.jar')
CP += ':' + ':'.join(extra)

METHOD_RE = re.compile(r'^\s*(?:public|private|protected|static|final|\s)*[\w<>\[\],.? ]+\s+(\w+)\s*\(([^;{)]*)\)')


def methods_with_annotation(text, ann='@SubscribeEvent'):
    """返回 [(行号, 方法名, [参数类型])]"""
    lines = text.split('\n')
    out = []
    for i, ln in enumerate(lines):
        if ann not in ln or ln.lstrip().startswith('*') or ln.lstrip().startswith('//'):
            continue
        for j in range(i + 1, min(i + 8, len(lines))):
            m = METHOD_RE.match(lines[j])
            if m and '(' in lines[j]:
                sig = lines[j]
                if '=' in sig.split('(')[0]:
                    continue
                params = m.group(2).strip()
                types = []
                if params:
                    depth = 0
                    cur = ''
                    for ch in params:
                        if ch == '<':
                            depth += 1
                        elif ch == '>':
                            depth -= 1
                        if ch == ',' and depth == 0:
                            types.append(cur)
                            cur = ''
                        else:
                            cur += ch
                    types.append(cur)
                    # 去掉参数名与注解，保留类型
                    cleaned = []
                    for t in types:
                        cleaned.append(t.strip())
                    types = cleaned
                out.append((j + 1, m.group(1), types))
                break
    return out


def resolve_type(t, imports, pkg):
    """把源码里的简单名解析成 javap 能认的全限定名（嵌套类用 $ 连接）。"""
    t = t.strip()
    t = re.sub(r'^@\w+(\([^)]*\))?\s*', '', t)
    t = re.sub(r'^(final|volatile|transient)\s+', '', t)
    t = re.sub(r'<.*$', '', t).strip()
    if not t:
        return None
    # 去掉参数名残留（如 "@Nullable ServerPlayer player" 已在上一步处理）
    parts = t.split(' ')
    if len(parts) > 1:
        t = parts[0]
    if t in ('int', 'long', 'double', 'float', 'boolean', 'byte', 'char', 'short', 'void'):
        return None
    seg = t.split('.')
    head = seg[0]
    if head in imports:
        base = imports[head]
        return base + ('$' + '$'.join(seg[1:]) if len(seg) > 1 else '')
    if head and head[0].islower() and '.' in t:
        return t
    if pkg:
        return pkg + '.' + head + ('$' + '$'.join(seg[1:]) if len(seg) > 1 else '')
    return None


_BUS_CACHE = {}


def _javap(cls):
    try:
        r = subprocess.run(['javap', '-cp', CP, cls], capture_output=True, text=True, timeout=30)
        if r.returncode != 0 or not r.stdout:
            return None
        return r.stdout
    except Exception:
        return None


def is_mod_bus_event(cls, seen=None):
    """递归判定：类自身或其父类/接口是否 implements IModBusEvent。
    javap 只列直接父类与直接接口，所以必须往上走。"""
    if cls in _BUS_CACHE:
        return _BUS_CACHE[cls]
    if seen is None:
        seen = set()
    if cls in seen:
        return False
    seen.add(cls)
    out = _javap(cls)
    if out is None:
        _BUS_CACHE[cls] = None
        return None
    if 'IModBusEvent' in out:
        _BUS_CACHE[cls] = True
        return True
    m = re.search(r'^\S.*\bclass\s+\S+\s+extends\s+([\w.$]+)', out, re.M)
    parents = []
    if m:
        parents.append(m.group(1))
    m2 = re.search(r'^(?:\S.*\b(?:class|interface)\s+\S+(?:\s+extends\s+[\w.$]+)?\s+implements\s+)([^{]+)', out, re.M)
    if m2:
        parents += [x.strip() for x in m2.group(1).split(',')]
    m3 = re.search(r'^\S.*\binterface\s+\S+\s+extends\s+([^{]+)', out, re.M)
    if m3:
        parents += [x.strip() for x in m3.group(1).split(',')]
    for p in parents:
        r = is_mod_bus_event(p, seen)
        if r:
            _BUS_CACHE[cls] = True
            return True
    _BUS_CACHE[cls] = False
    return False


files = []
for base, _, names in os.walk(ROOT):
    for n in names:
        if n.endswith('.java'):
            files.append(os.path.join(base, n))

all_types = {}
per_file = {}
for f in sorted(files):
    text = open(f, encoding='utf-8').read()
    ms = methods_with_annotation(text)
    if not ms:
        continue
    imports = {}
    for im in re.findall(r'^import\s+(?:static\s+)?([\w.]+)\s*;', text, re.M):
        imports[im.split('.')[-1]] = im
    pkg = 'net.ptcrys.fpsmatch'
    pm = re.search(r'^package\s+([\w.]+)\s*;', text, re.M)
    if pm:
        pkg = pm.group(1)
    declared = None
    m = re.search(r'@EventBusSubscriber\(([^)]*)\)', text, re.S)
    if m:
        b = re.search(r'bus\s*=\s*[\w.]*Bus\.(\w+)', m.group(1))
        declared = b.group(1) if b else 'GAME'
    manual = []
    if 'NeoForge.EVENT_BUS.register' in text:
        manual.append('EVENT_BUS.register')
    if 'modEventBus.register' in text or 'addListener' in text:
        manual.append('modEventBus')
    per_file[f] = (declared, manual, ms)
    for _, _, types in ms:
        for t in types:
            all_types.setdefault(t, None)

# 先解析每文件的简单名 -> FQN，再统一 javap
for f, (declared, manual, ms) in per_file.items():
    text = open(f, encoding='utf-8').read()
    imports = {}
    for im in re.findall(r'^import\s+(?:static\s+)?([\w.]+)\s*;', text, re.M):
        imports[im.split('.')[-1]] = im
    pkg = 'net.ptcrys.fpsmatch'
    pm = re.search(r'^package\s+([\w.]+)\s*;', text, re.M)
    if pm:
        pkg = pm.group(1)
    redone = []
    for ln, name, types in ms:
        redone.append((ln, name, [resolve_type(t, imports, pkg) for t in types]))
    per_file[f] = (declared, manual, redone)

for f, (declared, manual, ms) in per_file.items():
    for _, _, types in ms:
        for t in types:
            if t:
                all_types.setdefault(t, None)

for t in sorted(all_types):
    all_types[t] = is_mod_bus_event(t)

print('=== @SubscribeEvent 参数类型 → 是否 mod 总线事件 ===')
for t, v in sorted(all_types.items(), key=lambda kv: (kv[1] is not True, kv[0])):
    print('%-6s %s' % ('MOD' if v else ('game' if v is False else '??'), t))

print()
print('=== 不匹配（类声明/注册总线 vs 方法事件总线）===')
bad = 0
for f, (declared, manual, ms) in sorted(per_file.items()):
    for ln, name, types in ms:
        for t in types:
            v = all_types.get(t)
            if v is None:
                continue
            # 类走 game 总线（@EventBusSubscriber 默认/显式 GAME，或 EVENT_BUS.register(this)），
            # 方法却收 mod 总线事件 ⇒ 1.21.1 会在 register 时抛异常
            if v and declared in (None, 'GAME') and 'EVENT_BUS.register' in manual:
                print('!! %s:%d %s(%s)  ← game 总线注册但收 mod 总线事件' % (f.replace(ROOT + '/', ''), ln, name, t))
                bad += 1
            elif v and declared == 'GAME':
                print('!! %s:%d %s(%s)  ← @EventBusSubscriber(GAME) 但收 mod 总线事件' % (f.replace(ROOT + '/', ''), ln, name, t))
                bad += 1
print('共 %d 处' % bad)
