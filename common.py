from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=2560,1440')
options.add_argument('--mute-audio')
options.add_argument('--disable-gpu')
