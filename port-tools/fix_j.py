#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
幂等归一 / 双写修复：把 `TextColor.parseColor(...).result().orElseThrow()` 上被叠加多次的后缀折叠回一个。

背景（如实记录）：`tools/fix_f.py` 的第一版把 parseColor 规则写成「在调用后追加
`.result().orElseThrow()`」，重跑时会在已改好的代码上再追加一次，产出
`...orElseThrow().result().orElseThrow()`（无法编译）。现已修好 fix_f（规则自带归一），
本脚本用于**修复历史上被叠加的产物**，并作为幂等自检入口。

用法：
  python3 tools/fix_j.py          # 归一 + 报告
  python3 tools/fix_j.py --check  # 只报告，不写文件（供 CI/自检）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')

# 需要归一的双写形态：同一个后缀重复 ≥2 次
DOUBLE_ORELSE = re.compile(r'(\.result\(\)\.orElseThrow\(\)){2,}')
# 通用防线：任何「A.A」式完全重复的链式后缀（保守，只报不改）
DUP_CHAIN = re.compile(r'\.result\(\)\.orElseThrow\(\)\.result\(\)')


def main():
    check = '--check' in sys.argv
    total = 0
    files = []
    for base, _, names in os.walk(ROOT):
        for name in sorted(names):
            if not name.endswith('.java'):
                continue
            p = os.path.join(base, name)
            rel = p.replace(ROOT + '/', '')
            text = open(p, encoding='utf-8').read()
            new, n = DOUBLE_ORELSE.subn('.result().orElseThrow()', text)
            if n:
                total += n
                files.append((rel, n))
                if not check:
                    open(p, 'w', encoding='utf-8').write(new)

    print('== fix_j 双写归一 ==')
    print('  折叠站点 %d 处，涉及文件 %d 个' % (total, len(files)))
    for rel, n in files:
        print('    %-70s %d' % (rel, n))

    # 自检：归一之后不应再有重复后缀
    residual = []
    for base, _, names in os.walk(ROOT):
        for name in names:
            if not name.endswith('.java'):
                continue
            p = os.path.join(base, name)
            t = open(p, encoding='utf-8').read()
            c = len(DOUBLE_ORELSE.findall(t)) + len(DUP_CHAIN.findall(t))
            if c:
                residual.append((p.replace(ROOT + '/', ''), c))
    if residual:
        print('  !! 归一后仍有残留：')
        for rel, c in residual:
            print('    %s %d' % (rel, c))
        sys.exit(1)
    print('  自检通过：无重复后缀残留')


if __name__ == '__main__':
    main()
