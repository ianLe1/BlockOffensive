#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1.21.1 移植定点修复 I：gametest 的反射断言要捕获 NoSuchMethodException。

`Class#getMethod` 抛受检 `NoSuchMethodException`，javac 要求捕获或声明。
把 shopResultChannelIsRegistered 里的反射断言改成 try/catch 形式（语义：取不到方法即契约不满足）。
幂等。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'src', 'main', 'java')
REL = 'net/ptcrys/blockoffensive/gametest/ShopDropGameTests.java'

OLD = '''        helper.assertTrue(java.lang.reflect.Modifier.isStatic(
                        packetClass.getMethod("encode", packetClass, FriendlyByteBuf.class).getModifiers())
                        && java.lang.reflect.Modifier.isStatic(
                        packetClass.getMethod("decode", FriendlyByteBuf.class).getModifiers()),
                "shop action result must satisfy the reflective payload contract before purchases");'''

NEW = '''        boolean contract;
        try {
            contract = java.lang.reflect.Modifier.isStatic(
                    packetClass.getMethod("encode", packetClass, FriendlyByteBuf.class).getModifiers())
                    && java.lang.reflect.Modifier.isStatic(
                    packetClass.getMethod("decode", FriendlyByteBuf.class).getModifiers());
        } catch (NoSuchMethodException e) {
            contract = false;
        }
        helper.assertTrue(contract,
                "shop action result must satisfy the reflective payload contract before purchases");'''


def main():
    dry = '--dry' in sys.argv
    p = os.path.join(ROOT, REL)
    text = open(p, encoding='utf-8').read()
    if NEW in text:
        print('已经是目标形态，无需改动')
        return
    n = text.count(OLD)
    if n != 1:
        raise SystemExit('未命中（期望 1，实际 %d）：%s' % (n, REL))
    print('== fix_i 命中 ==\n  %s: 反射断言 try/catch  1' % REL)
    if not dry:
        open(p, 'w', encoding='utf-8').write(text.replace(OLD, NEW))


if __name__ == '__main__':
    main()
