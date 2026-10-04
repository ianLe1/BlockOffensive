#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 compile-N.log 的错误按「文件:行」整理，带源码行与 javac 的 符号/位置 明细。

用法：
  python3 tools/errs.py compile-3.log                 # 全量摘要（按文件）
  python3 tools/errs.py compile-3.log <正则>           # 只列符号/信息匹配该正则的站点（带源码行）
  python3 tools/errs.py compile-3.log <正则> --src     # 额外打印源码上下文
"""
import re
import sys
import collections

log = sys.argv[1] if len(sys.argv) > 1 else 'compile-3.log'
pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None

lines = open(log, encoding='utf-8', errors='replace').read().split('\n')
errs = []
for i, l in enumerate(lines):
    m = re.match(r'^(/.*\.java):(\d+): 错误: (.*)$', l)
    if not m:
        continue
    det = []
    for j in range(i + 1, min(i + 7, len(lines))):
        s = lines[j].strip()
        if re.match(r'^(符号|位置|需要|找到|原因):', s):
            det.append(s)
    errs.append({'file': m.group(1).split('/src/main/java/')[-1], 'line': int(m.group(2)),
                 'msg': m.group(3), 'det': det})

if pat:
    sel = [e for e in errs if pat.search(e['msg']) or any(pat.search(d) for d in e['det'])]
    byf = collections.OrderedDict()
    for e in sel:
        byf.setdefault(e['file'], []).append(e)
    print('匹配 %d 条，分布 %d 个文件' % (len(sel), len(byf)))
    for f, es in byf.items():
        print('\n── %s  (%d)' % (f, len(es)))
        for e in es:
            print('   %5d  %s' % (e['line'], e['msg']))
            for d in e['det']:
                print('          %s' % d)
else:
    byf = collections.Counter(e['file'] for e in errs)
    print('总错误 %d，文件 %d' % (len(errs), len(byf)))
    for f, n in byf.most_common():
        print('  %4d  %s' % (n, f))
