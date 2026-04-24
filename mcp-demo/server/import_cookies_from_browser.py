#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从浏览器手动导入 AWS OpenSearch Cookies

使用说明：
1. 在浏览器中打开 OpenSearch Dashboards 并登录
2. 打开开发者工具 (F12 或 Cmd+Option+I)
3. 在 Console 标签中执行以下 JavaScript 代码复制 cookies：

   copy(JSON.stringify(document.cookie.split('; ').reduce((acc, cookie) => {
       const [name, value] = cookie.split('=');
       acc[name] = value;
       return acc;
   }, {}), null, 2))

4. 将复制的内容粘贴到本脚本提示的位置

Author: FlyAIBox
Date: 2026-04-24
"""

import json
import sys


def import_cookies_from_string():
    """从复制的 cookie 字符串导入"""
    print("\n" + "=" * 80)
    print("📋 从浏览器导入 Cookies")
    print("=" * 80)
    print("\n说明：")
    print("1. 在浏览器中打开 OpenSearch Dashboards 并登录")
    print("2. 打开开发者工具 (F12 或 Cmd+Option+I)")
    print("3. 在 Console 标签中执行以下代码:\n")
    print("   " + "-" * 70)
    print("""   copy(JSON.stringify(document.cookie.split('; ').reduce((acc, cookie) => {
       const [name, value] = cookie.split('=');
       acc[name] = value;
       return acc;
   }, {}), null, 2))""")
    print("   " + "-" * 70)
    print("\n4. 粘贴复制的内容（输入完成后按两次回车）:\n")

    # 读取多行输入
    lines = []
    empty_count = 0
    while True:
        line = input()
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
        else:
            empty_count = 0
            lines.append(line)

    cookie_string = "\n".join(lines)

    if not cookie_string.strip():
        print("❌ 没有输入内容")
        return

    try:
        # 解析 JSON
        cookies_dict = json.loads(cookie_string)

        # 检查必需的 cookies
        required_cookies = ['REFRESH-TOKEN', 'ID-TOKEN', 'ACCESS-TOKEN']
        missing = [c for c in required_cookies if c not in cookies_dict]

        if missing:
            print(f"\n⚠️  警告：缺少以下关键 cookies: {', '.join(missing)}")
            print("这可能导致认证失败")

        # 转换为 Playwright 格式（数组）
        cookies_array = []
        for name, value in cookies_dict.items():
            cookies_array.append({
                "name": name,
                "value": value,
                "domain": ".ap-southeast-1.es.amazonaws.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax"
            })

        # 保存到文件
        with open('../opensearch_cookies.json', 'w') as f:
            json.dump(cookies_array, f, indent=2)

        print(f"\n✅ 成功导入 {len(cookies_array)} 个 cookies")
        print("✅ 已保存到 opensearch_cookies.json")

        # 显示关键 cookies
        print("\n🔑 关键 Cookies 检查:")
        for cookie_name in required_cookies:
            found = cookie_name in cookies_dict
            status = "✅" if found else "❌"
            print(f"   {status} {cookie_name}")

    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
        print("请确保粘贴的是有效的 JSON 格式")
    except Exception as e:
        print(f"\n❌ 导入失败: {e}")


def import_cookies_from_network_tab():
    """从浏览器 Network 标签复制的 Cookie 字符串导入"""
    print("\n" + "=" * 80)
    print("🌐 从 Network 标签导入 Cookies")
    print("=" * 80)
    print("\n说明：")
    print("1. 在浏览器中打开 OpenSearch Dashboards 并登录")
    print("2. 打开开发者工具 -> Network 标签")
    print("3. 刷新页面，选择任意请求")
    print("4. 在 Request Headers 中找到 'Cookie:' 行")
    print("5. 复制整个 Cookie 字符串（不包括 'Cookie:' 前缀）")
    print("\n请粘贴 Cookie 字符串:\n")

    cookie_string = input().strip()

    if not cookie_string:
        print("❌ 没有输入内容")
        return

    try:
        # 解析 cookie 字符串
        cookies_dict = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                name, value = item.split('=', 1)
                cookies_dict[name.strip()] = value.strip()

        # 检查必需的 cookies
        required_cookies = ['REFRESH-TOKEN', 'ID-TOKEN', 'ACCESS-TOKEN']
        missing = [c for c in required_cookies if c not in cookies_dict]

        if missing:
            print(f"\n⚠️  警告：缺少以下关键 cookies: {', '.join(missing)}")
            print("这可能导致认证失败")

        # 转换为 Playwright 格式
        cookies_array = []
        for name, value in cookies_dict.items():
            cookies_array.append({
                "name": name,
                "value": value,
                "domain": ".ap-southeast-1.es.amazonaws.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax"
            })

        # 保存到文件
        with open('../opensearch_cookies.json', 'w') as f:
            json.dump(cookies_array, f, indent=2)

        print(f"\n✅ 成功导入 {len(cookies_array)} 个 cookies")
        print("✅ 已保存到 opensearch_cookies.json")

        # 显示关键 cookies
        print("\n🔑 关键 Cookies 检查:")
        for cookie_name in required_cookies:
            found = cookie_name in cookies_dict
            status = "✅" if found else "❌"
            print(f"   {status} {cookie_name}")

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")


def main():
    print("\n" + "=" * 80)
    print("🍪 AWS OpenSearch Cookies 导入工具")
    print("=" * 80)
    print("\n请选择导入方式：")
    print("  1. 从 Console 复制 JSON 格式（推荐）")
    print("  2. 从 Network 标签复制 Cookie 字符串")
    print("  3. 退出")
    print("=" * 80)

    choice = input("\n请输入选项 (1/2/3): ").strip()

    if choice == "1":
        import_cookies_from_string()
    elif choice == "2":
        import_cookies_from_network_tab()
    elif choice == "3":
        print("\n👋 再见！")
    else:
        print("\n❌ 无效选项")


if __name__ == "__main__":
    main()
