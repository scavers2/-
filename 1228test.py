import os
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 设置是否以无头模式运行浏览器（True = 无头模式，False = 有头模式）
HEADLESS = False
EDGE_DRIVER_PATH = r"C:\Users\Administrator\Downloads\edgedriver_win64\msedgedriver.exe"
KEYWORDS = ["我好帅"]
AD_KEYWORDS = ["无痛人流", "小本加盟", "IT培训", "免费领pos机", "学历提升", "婚恋网", "装修", "房产中介", "成人教育",
               "公考机构", "考研机构", "办理信用卡"]
MAX_RESULTS = 100
OUTPUT_FILE = "link.txt"
MESSAGES_TO_SEND = [
    "发送",
    "在线咨询",
    "在线客服",
    "点击发送",
    "点击咨询",
]
def wait_page_ready(driver):
    """等待页面加载完成"""
    WebDriverWait(driver, 25).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def load_links(filename: str) -> list[str]:
    """从文件中读取链接，每行一个"""
    if not os.path.exists(filename):
        print(f"❌ 文件不存在：{filename}")
        return []

    links = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                links.append(url)

    if not links:
        print(f"⚠ {filename} 文件为空，未找到任何有效链接。")
        return []

    return links


def save_links(links: list[str], filename: str):
    """将广告链接保存到文件"""
    if not links:
        print("\n⚠ 没有抓取到广告链接，无法保存。")
        return

    out_path = os.path.abspath(filename)
    with open(out_path, "w", encoding="utf-8") as f:
        for link in links:
            f.write(link + "\n")

    print(f"\n💾 已保存 {len(links)} 条广告链接到：{out_path}")


def collect_baidu_ad_links(driver, keyword: str, max_results: int) -> list[str]:
    """从百度搜索结果中提取【带“广告”标识】的结果链接。"""
    ad_links = []
    seen = set()

    # 构建搜索 URL
    search_url = f"https://www.baidu.com/s?wd={quote_plus(keyword)}"
    print(f"\n🔍 正在进行关键词 '{keyword}' 的百度搜索...")

    # 打开搜索结果页
    driver.get(search_url)
    wait_page_ready(driver)

    # 开始滚动，加载更多广告
    auto_scroll(driver)

    containers = driver.find_elements(
        By.CSS_SELECTOR,
        "div.result, div.c-container, div.ec_container, div.c-container.ec-container"
    )

    print(f"检测到可能结果块：{len(containers)}")

    for block in containers:
        try:
            if "广告" not in block.text:
                continue

            link_element = None
            for a in block.find_elements(By.CSS_SELECTOR, "a[href]"):
                href = a.get_attribute("href") or ""
                if href.startswith("http://") or href.startswith("https://"):
                    link_element = a
                    break

            if not link_element:
                continue

            href = link_element.get_attribute("href") or ""
            if not href or href in seen:
                continue

            seen.add(href)
            ad_links.append(href)

            if len(ad_links) >= max_results:
                break

        except Exception:
            continue

    return ad_links


def auto_scroll(driver):
    """简单的滚动页面函数，触发懒加载。"""
    last_height = driver.execute_script("return document.body.scrollHeight")
    rounds = 0
    SCROLL_MAX_ROUNDS = 5  # 控制滚动次数
    SCROLL_PAUSE = 0.6  # 每次滚动后的暂停时间

    while rounds < SCROLL_MAX_ROUNDS:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        rounds += 1
        if new_height == last_height:
            break
        last_height = new_height


def looks_like_cloudflare_page(driver) -> bool:
    """粗略判断是否被 Cloudflare 拦截（特征字符串/节点）"""
    try:
        html = driver.page_source.lower()
        keywords = [
            "verify you are human",
            "checking your browser",
            "cloudflare",
            "cf-challenge",
            "managed challenge",
            "turn on javascript",
        ]
        if any(k in html for k in keywords):
            return True
        # challenge 可能在 iframe 里
        els = driver.find_elements(By.CSS_SELECTOR, "[id*='cf-'], [class*='cf-']")
        if els:
            return True
    except Exception:
        pass
    return False


def ensure_manual_pass(driver, reason: str = "需要通过 Cloudflare 验证/人机验证"):
    """暂停等待你手动通过验证后再继续"""
    print(f"\n⚠ {reason}：请在已打开的浏览器窗口中完成验证。")
    print("完成后回到本控制台，按回车继续采集...")
    try:
        input()
    except EOFError:
        # 某些 IDE 环境可能无 stdin；退而求其次给点时间
        print("环境无 stdin，暂停 60 秒等待你完成验证...")
        time.sleep(60)
    # 再等页面稳定一下
    time.sleep(1.5)


def click_buy_like_button(driver):
    "发送",
    "在线咨询",
    "在线客服",
    "点击发送",
    "点击咨询",
    try:
        time.sleep(3)  # 给页面一点加载时间
        print("🔍 正在查找购买/咨询相关按钮...")

        keywords = ["buy", "buy now", "shop", "shop now", "add to cart", "order now", "点击咨询"]

        candidates = driver.find_elements(
            By.XPATH,
            "//button | //a | //input[@type='button' or @type='submit']"
        )

        target = None

        for el in candidates:
            try:
                text = (el.text or "").strip()
                if not text:
                    text = (el.get_attribute("value") or "").strip()
                if not text:
                    text = (el.get_attribute("aria-label") or "").strip()
                if not text:
                    continue

                text_low = text.lower()

                if any(k in text_low for k in keywords):
                    target = el
                    break
            except Exception:
                continue

        if target:
            label = (
                    target.text
                    or target.get_attribute("value")
                    or target.get_attribute("aria-label")
                    or ""
            ).strip()
            print(f"✅ 找到按钮：{label!r}")
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", target
                )
                time.sleep(0.8)
                target.click()
                print("👉 已点击按钮，等待页面响应...")
            except Exception as e:
                print(f"⚠ 点击按钮失败：{e!r}")
        else:
            print("⚠ 未找到匹配 BUTTON_KEYWORDS 的按钮，跳过点击。")

    except Exception as e:
        print(f"⚠ click_buy_like_button 出错：{e!r}")


def send_messages(driver):
    "你好",
    "你好",
    "我想要资料，谢谢",
    "手机号：15689668666",
    "谢谢",
    # 假设找到的输入框通常有“请详细描述您的问题”这类提示文本
    input_field = None
    try:
        input_field = driver.find_element(By.XPATH, "//textarea[contains(@placeholder, '请详细描述您的问题')]")
    except Exception:
        pass

    if input_field:
        for message in MESSAGES_TO_SEND:
            input_field.send_keys(message)
            input_field.send_keys(Keys.RETURN)  # 模拟回车键发送消息
            print(f"✅ 发送消息：'{message}'")
            time.sleep(60)  # 每次消息之间间隔 60 秒
    else:
        print("⚠ 未找到输入框，无法发送消息。")


def main():
    # 配置 Edge
    opts = EdgeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Edge(
        service=EdgeService(executable_path=EDGE_DRIVER_PATH),
        options=opts
    )

    try:
        # 第一步：打开百度并搜索“你好帅”（仅用于等待）
        print("⚠ 程序已启动，正在搜索 '你好帅'...")
        driver.get("https://www.baidu.com")
        wait_page_ready(driver)

        # 构建搜索 URL，直接跳转
        search_url = f"https://www.baidu.com/s?wd={quote_plus('你好帅')}"
        driver.get(search_url)

        # 等待页面加载完成
        wait_page_ready(driver)

        # 第二步：停留 2 分钟（给用户时间手动验证）
        print("⚠ 请在 2 分钟内手动完成百度的验证，程序暂停 2 分钟...")
        time.sleep(120)  # 暂停2分钟

        # 第三步：执行搜索KEYWORDS中的内容
        all_ad_links = []
        for keyword in AD_KEYWORDS:
            print(f"\n开始处理关键词：'{keyword}'")
            ad_links = collect_baidu_ad_links(driver, keyword, MAX_RESULTS)
            all_ad_links.extend(ad_links)

        # 保存所有广告链接到 link.txt
        save_links(all_ad_links, OUTPUT_FILE)

        if not all_ad_links:
            print("⚠ 没有找到任何广告链接，流程结束。")
            return

        # 读取 link.txt 中的所有链接并继续处理
        links_from_file = load_links(OUTPUT_FILE)
        open_links_and_interact(driver, links_from_file)

        # 发送消息到找到的输入框
        send_messages(driver)

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
