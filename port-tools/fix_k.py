#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
让随包的 JUnit 5 单测在**离线**环境也能编译/运行。

背景：`src/test/java/.../CSEconomyRulesTest.java` 依赖 `org.junit.jupiter.*`，
但本机 Gradle 缓存里只有 `junit-bom` 的 pom、没有 junit jar，且 `--offline` 不能下载，
于是 `./gradlew build` 在 `:compileTestJava` 阶段失败（主 jar 其实已产出）。

处置：把 JUnit 5.10.2 的 7 个 jar 一次性下载进 `libs/test/`（fileTree 依赖，
离线可解析，不进主 jar、不改变运行时行为），并在 build.gradle 里加
`testImplementation fileTree(dir: 'libs/test', include: ['*.jar'])`。

幂等：jar 已存在且非空则跳过下载；build.gradle 已含该行则跳过改写。
用法：python3 tools/fix_k.py [--dry]
"""
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..'))
DEST = os.path.join(PROJ, 'libs', 'test')
BUILD = os.path.join(PROJ, 'build.gradle')

M = 'https://repo1.maven.org/maven2/'
JARS = [
    'org/junit/jupiter/junit-jupiter-api/5.10.2/junit-jupiter-api-5.10.2.jar',
    'org/junit/jupiter/junit-jupiter-engine/5.10.2/junit-jupiter-engine-5.10.2.jar',
    'org/junit/platform/junit-platform-commons/1.10.2/junit-platform-commons-1.10.2.jar',
    'org/junit/platform/junit-platform-engine/1.10.2/junit-platform-engine-1.10.2.jar',
    'org/junit/platform/junit-platform-launcher/1.10.2/junit-platform-launcher-1.10.2.jar',
    'org/opentest4j/opentest4j/1.3.0/opentest4j-1.3.0.jar',
    'org/apiguardian/apiguardian-api/1.1.2/apiguardian-api-1.1.2.jar',
]

LINE = "    testImplementation fileTree(dir: 'libs/test', include: ['*.jar'])"
ANCHOR = "    compileOnly fileTree(dir: 'libs', include: ['*.jar'])\n"
COMMENT = "    // 随包 JUnit 5 单测（离线：jar 预先放在 libs/test/，见 tools/fix_k.py）\n"


def main():
    dry = '--dry' in sys.argv
    os.makedirs(DEST, exist_ok=True)
    got = 0
    for rel in JARS:
        name = os.path.basename(rel)
        out = os.path.join(DEST, name)
        if os.path.exists(out) and os.path.getsize(out) > 2000:
            print('  已存在 %s' % name)
            continue
        print('  下载 %s' % name)
        if dry:
            continue
        with urllib.request.urlopen(M + rel, timeout=60) as r:
            data = r.read()
        if len(data) < 2000:
            raise SystemExit('下载异常（%d 字节）：%s' % (len(data), rel))
        with open(out, 'wb') as f:
            f.write(data)
        got += 1
    print('  新下载 %d 个' % got)

    text = open(BUILD, encoding='utf-8').read()
    if LINE.strip() in text:
        print('  build.gradle 已含 testImplementation，跳过')
        add_use_junit_platform()
        return
    if ANCHOR not in text:
        raise SystemExit('build.gradle 锚点未命中')
    text = text.replace(ANCHOR, ANCHOR + COMMENT + LINE + '\n', 1)
    if not dry:
        open(BUILD, 'w', encoding='utf-8').write(text)
    print('  build.gradle 已加入 testImplementation fileTree(libs/test)')
    add_use_junit_platform()


TEST_ANCHOR = "tasks.withType(JavaCompile).configureEach {\n"
TEST_BLOCK = '''tasks.named('test', Test).configure {
    // Gradle 默认走 JUnit 4 引擎，会把 JUnit 5 测试静默跳过（报 0 个测试）；
    // 显式启用 JUnit Platform，随包单测才真的执行。
    useJUnitPlatform()
    testLogging {
        events 'passed', 'failed', 'skipped'
        exceptionFormat 'full'
        showStandardStreams = false
    }
}

'''


def add_use_junit_platform():
    text = open(BUILD, encoding='utf-8').read()
    if "useJUnitPlatform()" in text:
        print('  build.gradle 已含 useJUnitPlatform()，跳过')
        return
    if TEST_ANCHOR not in text:
        raise SystemExit('build.gradle 缺少 JavaCompile 锚点')
    text = text.replace(TEST_ANCHOR, TEST_BLOCK + TEST_ANCHOR, 1)
    open(BUILD, 'w', encoding='utf-8').write(text)
    print('  build.gradle 已加入 useJUnitPlatform()')


if __name__ == '__main__':
    main()
