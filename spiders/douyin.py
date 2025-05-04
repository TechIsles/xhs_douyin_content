import os, sys
import time
import glob
import pickle
# 忽略 openpyxl 样式警告
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 自动添加项目根目录到 sys.path
from utils.init_path import setup_project_root
setup_project_root()

from project_config.project import driver_path, pkl_path, get_full_cookie_paths, dy_file_path

class Douyin:
    def __init__(self, url, cookies_file):
        self.url = url
        self.cookies_file = cookies_file
        self.data_center_url = "https://creator.douyin.com/creator-micro/data-center/content"

        edge_options = Options()
        edge_options.add_experimental_option("prefs", {
            "download.default_directory": str(dy_file_path),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        self.driver = webdriver.Edge(
            service=Service(str(driver_path)),
            options=edge_options
        )
        self.driver.maximize_window()

    def load_cookies(self):
        try:
            with open(self.cookies_file, "rb") as cookie_file:
                cookies = pickle.load(cookie_file)
                self.driver.get(self.url)
                self.driver.delete_all_cookies()
                for cookie in cookies:
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    self.driver.add_cookie(cookie)
                self.driver.refresh()
                print(f"✅ Loaded cookies from {self.cookies_file}")
                self._post_login_flow()
        except FileNotFoundError:
            print(f"❌ Cookie file not found: {self.cookies_file}")

    def _post_login_flow(self):
        self.driver.get(self.data_center_url)
        self.wait_for_page_ready()
        self.click_tgzp_tab()
        self.click_post_list_tab()
        # self.input_start_date()
        # self.input_end_date()
        self.click_export_data_button()

    def wait_for_page_ready(self, timeout=30):
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == 'complete'
        )

    def click_tgzp_tab(self):
        locator = (By.XPATH, "//div[@id='semiTab1' and text()='投稿作品']")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(locator)
            )
            self.driver.execute_script("arguments[0].click();", element)
            print("✅ 点击“投稿作品”成功")
        except Exception as e:
            print(f"❌ 点击“投稿作品”失败: {e}")

    def click_post_list_tab(self):
        locator = (By.XPATH, "//div[@id='semiTabPanel1']//span[contains(@class, 'douyin-creator-pc-radio-addon') and normalize-space(text())='投稿列表']")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(locator)
            )
            self.driver.execute_script("arguments[0].click();", element)
            print("✅ 点击“投稿列表”成功")
        except Exception as e:
            print(f"❌ 点击“投稿列表”失败: {e}")

    def input_start_date(self):
        locator = (By.XPATH, "//div[@id='semiTabPanel1']//input[@placeholder='开始日期']")
        ninety_days_ago = datetime.now() - timedelta(days=90)
        min_date = datetime(2025, 3, 4)
        target_date = max(ninety_days_ago, min_date).strftime("%Y-%m-%d")
        self._fill_date(locator, target_date, "开始日期")

    def input_end_date(self):
        locator = (By.XPATH, "//div[@id='semiTabPanel1']//input[@placeholder='结束日期']")
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self._fill_date(locator, target_date, "结束日期")

    def _fill_date(self, locator, date_str, label):
        try:
            input_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(locator)
            )
            self.driver.execute_script("arguments[0].removeAttribute('readonly')", input_element)
            self.driver.execute_script("arguments[0].value = arguments[1];", input_element, date_str)
            self.driver.execute_script("""
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, input_element)
            print(f"✅ 输入{label}：{date_str}")
        except Exception as e:
            print(f"❌ 设置{label}失败: {e}")

    def click_export_data_button(self):
        locator = (By.XPATH, "//div[contains(@class,'container-ttkmFy')]//button[.//span[text()='导出数据']]")
        try:
            time.sleep(2)
            button = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(locator)
            )
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            self.driver.execute_script("arguments[0].click();", button)
            print("✅ 点击导出数据成功")
        except Exception as e:
            print(f"❌ 点击导出数据失败: {e}")

    def run(self):
        try:
            self.load_cookies()
            time.sleep(10)
        except Exception as e:
            print(f"运行出错：{e}")
        finally:
            self.driver.quit()

    @classmethod
    def cleanup_temp_files(cls, output_path, keyword="data"):
        deleted = 0
        for file in glob.glob(os.path.join(output_path, f"*{keyword}*.xlsx")):
            try:
                os.remove(file)
                print(f"🗑️ 已删除临时文件: {file}")
                deleted += 1
            except Exception as e:
                print(f"❌ 删除失败: {file}，错误: {e}")
        if deleted == 0:
            print("⚠️ 没有发现需要删除的临时文件")

    @classmethod
    def merge_xlsx_files(cls, output_path):
        all_files = glob.glob(os.path.join(output_path, "*data*.xlsx"))
        df_list = []
        for file in all_files:
            try:
                df = pd.read_excel(file)
                df["来源文件"] = os.path.basename(file)
                df_list.append(df)
            except Exception as e:
                print(f"⚠️ 无法读取 {file}: {e}")

        if df_list:
            merged_df = pd.concat(df_list, ignore_index=True)
            final_file = os.path.join(output_path, "douyin_汇总数据.xlsx")
            merged_df.to_excel(final_file, index=False)
            print(f"📊 已成功导出汇总文件：{final_file}")
        else:
            print("❌ 没有可合并的xlsx文件")
            return

        # 删除合并前的单个数据文件
        cls.cleanup_temp_files(output_path, keyword="data")

    @classmethod
    def run_all(cls):
        cookie_paths = get_full_cookie_paths("douyin", pkl_path)
        for cookie_file in cookie_paths:
            print(f"\n🌐 当前账号: {cookie_file}")
            douyin = cls("https://creator.douyin.com/creator-micro/home", cookie_file)
            douyin.run()
            print("⏳ 等待下载完成...")
            time.sleep(15)

        print("\n📁 开始合并所有Excel文件...")
        cls.merge_xlsx_files(str(dy_file_path))

if __name__ == "__main__":
    Douyin.run_all()
