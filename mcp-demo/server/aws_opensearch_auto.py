#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS OpenSearch 自动登录客户端（Playwright）

自动完成 SSO 登录并获取数据

依赖: pip install playwright && playwright install

Author: FlyAIBox
Date: 2025.05.03
"""

import json
import asyncio
import os
from playwright.async_api import async_playwright


async def search_with_auto_login(query: str, username: str, password: str):
    """
    自动登录并搜索日志

    参数:
        query: 搜索关键词
        username: SSO 用户名
        password: SSO 密码
    """
    async with async_playwright() as p:
        # 启动浏览器（可以设置 headless=True 无头模式）
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. 访问 OpenSearch Dashboards
        print("正在访问 OpenSearch Dashboards...")
        await page.goto(
            'https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com/_dashboards'
        )

        # 2. 等待 SSO 登录页面加载
        print("等待 SSO 登录页面...")
        await page.wait_for_load_state('networkidle')

        # 3. 填写登录信息（根据实际 SSO 页面调整选择器）
        print("填写登录信息...")
        try:
            # 常见的 SSO 登录表单字段名
            # 你需要根据实际的 SSO 页面调整这些选择器
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')

            # 或者如果是其他选择器：
            # await page.fill('#username', username)
            # await page.fill('#password', password)
            # await page.click('#login-button')

        except Exception as e:
            print(f"登录表单填写失败: {e}")
            print("请检查 SSO 登录页面的实际字段名")

        # 4. 等待登录完成
        print("等待登录完成...")
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)  # 额外等待

        # 5. 获取登录后的 cookies
        cookies = await context.cookies()
        print(f"\n获取到 {len(cookies)} 个 cookies")

        # 保存 cookies 到文件（可重复使用）
        with open('opensearch_cookies.json', 'w') as f:
            json.dump(cookies, f, indent=2)
        print("Cookies 已保存到 opensearch_cookies.json")

        # 6. 访问 Discover 页面并搜索
        print(f"\n正在搜索: {query}")
        discover_url = (
            'https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com/'
            '_dashboards/app/discover#/?'
            '_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now-10h,to:now))'
            f'&_a=(query:(language:kuery,query:\'{query}\'))'
        )
        await page.goto(discover_url, wait_until='domcontentloaded')
        await page.wait_for_load_state('networkidle')

        # 7. 等待搜索结果加载
        print("\n等待搜索结果...")
        try:
            await page.wait_for_selector('[data-test-subj="docTable"]', timeout=30000)
            print("搜索结果表格已加载")
        except Exception as e:
            print(f"等待搜索结果超时: {e}")

        await asyncio.sleep(5)

        # 8. 提取搜索结果
        title = await page.title()
        print(f"当前页面标题: {title}")

        # 尝试提取搜索结果数量
        try:
            hits_element = await page.query_selector('[data-test-subj="discoverQueryHits"]')
            if hits_element:
                hits_text = await hits_element.inner_text()
                print(f"搜索结果数量: {hits_text}")
        except:
            print("无法获取搜索结果数量")

        # 截图
        await page.screenshot(path='search_results.png', full_page=True)
        print("搜索结果截图已保存到 search_results.png")

        await browser.close()


async def search_with_saved_cookies(query: str):
    """
    使用保存的 cookies 搜索（无需重新登录）

    参数:
        query: 搜索关键词
    """
    # 读取保存的 cookies
    try:
        with open('opensearch_cookies.json', 'r') as f:
            content = f.read().strip()
            if not content:
                print("❌ cookies 文件为空，请先手动登录获取 cookies")
                return
            cookies = json.loads(content)
    except FileNotFoundError:
        print("❌ 未找到保存的 cookies 文件 (opensearch_cookies.json)")
        print("请先手动登录或使用浏览器获取 cookies")
        return
    except json.JSONDecodeError as e:
        print(f"❌ cookies 文件格式错误: {e}")
        print("请检查 opensearch_cookies.json 文件格式")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # 设置 cookies
        await context.add_cookies(cookies)
        page = await context.new_page()

        # 直接访问搜索页面
        print(f"使用保存的 cookies 搜索: {query}")
        discover_url = (
            'https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com/'
            '_dashboards/app/discover#/?'
            '_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:now-10h,to:now))'
            f'&_a=(query:(language:kuery,query:\'{query}\'))'
        )
        await page.goto(discover_url, wait_until='domcontentloaded')
        print("页面已加载，等待搜索结果...")

        # 等待页面完全加载
        await page.wait_for_load_state('networkidle')

        # 等待搜索结果表格或日志列表出现（根据 OpenSearch Dashboards 的 DOM 结构）
        # 常见的选择器：
        try:
            # 等待文档列表或表格出现（超时 30 秒）
            await page.wait_for_selector('[data-test-subj="docTable"]', timeout=30000)
            print("搜索结果表格已加载")
        except Exception as e:
            print(f"等待搜索结果超时: {e}")
            print("尝试等待其他元素...")
            try:
                # 尝试其他可能的选择器
                await page.wait_for_selector('.discover-table', timeout=10000)
            except:
                print("未找到搜索结果元素，继续截图...")

        # 额外等待，确保数据渲染完成
        await asyncio.sleep(5)

        # 获取页面标题，确认是否在正确的页面
        title = await page.title()
        print(f"当前页面标题: {title}")

        # 截图（全页）
        await page.screenshot(path='search_results.png', full_page=True)
        print("搜索结果截图已保存（全页截图）")

        # 尝试提取搜索结果数量
        try:
            hits_element = await page.query_selector('[data-test-subj="discoverQueryHits"]')
            if hits_element:
                hits_text = await hits_element.inner_text()
                print(f"搜索结果数量: {hits_text}")
        except:
            print("无法获取搜索结果数量")

        await browser.close()


async def get_cookies_only():
    """
    只获取 cookies，不执行搜索（推荐用于首次配置）
    """
    async with async_playwright() as p:
        print("\n" + "=" * 80)
        print("🔐 AWS OpenSearch Cookies 获取工具")
        print("=" * 80)
        print("\n📝 说明：")
        print("  1. 浏览器会自动打开 AWS OpenSearch Dashboards")
        print("  2. 请手动完成 SSO 登录")
        print("  3. 登录成功后，cookies 会自动保存到 opensearch_cookies.json")
        print("  4. 看到 'Cookies 已保存' 提示后，可以关闭浏览器\n")

        input("按回车键继续...")

        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 访问 OpenSearch Dashboards
        print("\n正在打开 AWS OpenSearch Dashboards...")
        await page.goto(
            'https://search-ops-log-alpha-swcyckhzgta27vf7coznkw4k44.ap-southeast-1.es.amazonaws.com/_dashboards'
        )

        print("\n⏳ 请在浏览器中完成登录...")
        print("💡 提示：登录成功后会自动检测并保存 cookies")

        # 等待用户登录（检测 URL 变化或特定元素）
        try:
            # 等待跳转到 Dashboards 主页（登录成功的标志）
            await page.wait_for_url("**/_dashboards/app/**", timeout=300000)  # 5分钟超时
            print("\n✅ 检测到登录成功！")
        except Exception as e:
            print(f"\n⚠️  超时或登录失败: {e}")
            print("请确保已完成登录，将保存当前 cookies")

        # 额外等待确保 Cognito tokens 完全设置
        print("⏳ 等待 AWS Cognito tokens 加载...")
        await asyncio.sleep(50)

        # 检查关键 cookies 是否存在
        max_retries = 10
        retry_count = 0
        required_cookies = ['REFRESH-TOKEN', 'ID-TOKEN', 'ACCESS-TOKEN']

        while retry_count < max_retries:
            cookies = await context.cookies()
            cookie_names = [c['name'] for c in cookies]

            missing_cookies = [name for name in required_cookies if name not in cookie_names]

            if not missing_cookies:
                print(f"✅ 所有必需的 cookies 已加载")
                break
            else:
                print(f"⏳ 等待 cookies: {', '.join(missing_cookies)} (尝试 {retry_count + 1}/{max_retries})")
                await asyncio.sleep(2)
                retry_count += 1

        if missing_cookies:
            print(f"\n⚠️  警告：以下 cookies 未找到: {', '.join(missing_cookies)}")
            print("这可能导致认证失败，但仍然会保存当前的 cookies")

        # 获取并保存 cookies
        cookies = await context.cookies()
        print(f"\n📦 获取到 {len(cookies)} 个 cookies")

        # 显示关键 cookies
        print("\n🔑 关键 Cookies 检查:")
        for cookie_name in required_cookies:
            found = any(c['name'] == cookie_name for c in cookies)
            status = "✅" if found else "❌"
            print(f"   {status} {cookie_name}")

        # 显示所有 cookie 名称（用于调试）
        print(f"\n📋 所有 cookies: {', '.join([c['name'] for c in cookies])}")

        with open('opensearch_cookies.json', 'w') as f:
            json.dump(cookies, f, indent=2)

        print("✅ Cookies 已保存到 opensearch_cookies.json")
        print("\n下一步：")
        print("  - 配置 Claude Desktop 使用此 cookies 文件")
        print("  - 或运行此脚本测试搜索功能")

        input("\n按回车键关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 AWS OpenSearch 自动化工具")
    print("=" * 80)
    print("\n请选择模式：")
    print("  1. 🔐 获取 Cookies（首次使用或 cookies 过期）")
    print("  2. 🔍 使用已保存的 Cookies 搜索日志")
    print("  3. ❌ 退出")
    print("=" * 80)

    choice = input("\n请输入选项 (1/2/3): ").strip()

    if choice == "1":
        asyncio.run(get_cookies_only())
    elif choice == "2":
        # 检查 cookies 文件是否存在
        if not os.path.exists('opensearch_cookies.json'):
            print("\n❌ 未找到 opensearch_cookies.json 文件")
            print("请先选择选项 1 获取 cookies")
        else:
            query = input("\n请输入搜索关键词 (默认: ERROR): ").strip() or "ERROR"
            asyncio.run(search_with_saved_cookies(query=query))
    elif choice == "3":
        print("\n👋 再见！")
    else:
        print("\n❌ 无效选项")
