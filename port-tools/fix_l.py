#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
让产物 jar 可复现（reproducible build）。

问题：默认的 jar 任务把「文件时间戳」和「文件遍历顺序」写进 zip 条目，
同一份源码两次构建会得到不同 sha256（实测 c34a1471… vs 0c9a2737…），
使「jar 的 sha256」无法作为交付物的身份标识。

处置：对所有归档任务关闭时间戳、固定条目顺序。幂等。
用法：python3 tools/fix_l.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.join(HERE, '..', 'build.gradle'))

BLOCK = '''tasks.withType(AbstractArchiveTask).configureEach {
    // 可复现构建：不写文件时间戳、固定条目顺序（否则同源码两次构建 sha256 不同）
    preserveFileTimestamps = false
    reproducibleFileOrder = true
}

'''
ANCHOR = "tasks.named('test', Test).configure {\n"


def main():
    text = open(BUILD, encoding='utf-8').read()
    if 'preserveFileTimestamps' in text:
        print('  build.gradle 已含可复现构建配置，跳过')
        return
    if ANCHOR not in text:
        raise SystemExit('build.gradle 缺少 test 任务锚点')
    text = text.replace(ANCHOR, BLOCK + ANCHOR, 1)
    open(BUILD, 'w', encoding='utf-8').write(text)
    print('  build.gradle 已加入可复现构建配置')


if __name__ == '__main__':
    main()
