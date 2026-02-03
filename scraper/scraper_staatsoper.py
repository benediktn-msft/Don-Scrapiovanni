"""
Wiener Staatsoper ticket availability scraper
Runs once daily at 09:30 AM Austria time (with random ±2 minute offset)
Checks for ticket availability for tomorrow's show
"""
import logging
import os
import time
import random
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import pytz
import azure.functions as func
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

bp = func.Blueprint()

# Wiener Staatsoper base URL
STAATSOPER_URL = "https://tickets.wiener-staatsoper.at/webshop/webticket/eventlist"
AUSTRIA_TZ = pytz.timezone("Europe/Vienna")

def get_selenium_driver():
    """Create and configure a headless Chrome driver for Selenium"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.binary_location = "/usr/bin/chromium"
    
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def get_available_categories(driver, event_id):
    """Navigate to the bestseatselect page and extract available categories."""
    try:
        url = f"https://tickets.wiener-staatsoper.at/webshop/webticket/bestseatselect?eventId={event_id}&upsellNo=0"
        driver.get(url)
        time.sleep(5)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        category_divs = soup.find_all('div', id=re.compile(r'^category_\d+'))
        available_categories = []
        
        for cat_div in category_divs:
            h2 = cat_div.find('h2', id=re.compile(r'^seatgroup-\d+'))
            if h2:
                cat_text = h2.get_text(strip=True)
                match = re.search(r'Kategorie\s+(\d+)', cat_text)
                if match:
                    cat_num = int(match.group(1))
                    
                    # Skip if sold out
                    if cat_div.find('span', string=re.compile(r'Sold out', re.I)):
                        continue
                    
                    # Check for enabled input fields with data-max > 0
                    inputs = cat_div.find_all('input', type='number')
                    for inp in inputs:
                        data_max = inp.get('data-max', '0')
                        disabled = inp.get('disabled') is not None or inp.get('aria-hidden') == 'true'
                        try:
                            if int(data_max) > 0 and not disabled:
                                available_categories.append(cat_num)
                                break
                        except (ValueError, TypeError):
                            pass
        
        available_categories.sort()
        return available_categories
        
    except Exception as e:
        logging.warning(f"Error getting available categories: {e}")
        return []

def parse_date_time(date_text, time_text):
    """Parse Austrian date format and time, returns datetime in Austria timezone"""
    try:
        date_clean = re.sub(r'^[A-Za-zäöüÄÖÜß]+\.\s*', '', date_text.strip())
        date_parts = date_clean.split('.')
        if len(date_parts) != 3:
            return None
        
        day, month, year = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
        time_parts = time_text.strip().split(':')
        if len(time_parts) != 2:
            return None
        
        hour, minute = int(time_parts[0]), int(time_parts[1])
        dt = datetime(year, month, day, hour, minute)
        return AUSTRIA_TZ.localize(dt)
    except Exception as e:
        logging.error(f"Error parsing date/time: {e}")
        return None

def send_telegram_message(message):
    """Send Telegram notification using environment variables"""
    import requests
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token or not telegram_chat_id:
        logging.warning("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Telegram failed: {e}")
        return False

@bp.timer_trigger(schedule="0 30 9 * * *", arg_name="mytimer", run_on_startup=False)
def staatsoper_scraper(mytimer: func.TimerRequest) -> None:
    """Wiener Staatsoper ticket availability checker"""
    logging.info("Starting Wiener Staatsoper Scraper...")
    
    # Add random delay (0-4 minutes) to run between 09:30 and 09:34
    now = datetime.now(AUSTRIA_TZ)
    if now.hour == 9 and now.minute == 30:
        random_delay = random.randint(0, 4)
        if random_delay > 0:
            time.sleep(random_delay * 60)
    
    now = datetime.now(AUSTRIA_TZ)
    tomorrow = (now + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%d.%m.%Y")
    logging.info(f"Looking for tickets for: {tomorrow_str}")
    
    driver = None
    try:
        driver = get_selenium_driver()
        driver.get(STAATSOPER_URL)
        time.sleep(3)
        
        # Handle inactivity page
        page_source = driver.page_source
        if "Sie waren längere Zeit inaktiv" in page_source or "Reservierungsvorgang wurde beendet" in page_source:
            logging.info("Inactivity page detected, clicking 'Weiter'...")
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-default.full-width[href='/webshop/webticket/shop']")
                if not elements:
                    elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'Weiter') and contains(@href, '/webshop/webticket/shop')]")
                for element in elements:
                    if element.is_displayed() and "Weiter" in element.text:
                        element.click()
                        time.sleep(5)
                        break
            except Exception as e:
                logging.warning(f"Could not click 'Weiter': {e}")
        
        # Handle cookie consent
        time.sleep(2)
        try:
            # Try ccm19 accept button
            ccm19_elements = driver.find_elements(By.CSS_SELECTOR, "#ccm19_module, .ccm19_module")
            if ccm19_elements:
                accept_buttons = ccm19_elements[0].find_elements(By.XPATH, ".//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'akzeptieren')] | .//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]")
                for btn in accept_buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(2)
                        break
        except Exception:
            pass
        
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Wait for events to load
        for i in range(15):
            page_source = driver.page_source
            if "selectseat?eventId=" in page_source:
                break
            time.sleep(2)
            if i % 3 == 0:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
        
        time.sleep(3)
        
        # Parse events
        soup = BeautifulSoup(driver.page_source, "html.parser")
        event_list_ul = soup.find("ul", id="eventListUl")
        if not event_list_ul:
            logging.warning("Event list not found")
            return
        
        event_lis = event_list_ul.find_all("li", recursive=False)
        if len(event_lis) == 0:
            logging.warning("No events found")
            return
        
        events_found = []
        
        for li in event_lis:
            event_div = li.find("div", class_=lambda x: x and "evt-event" in x if x else False)
            if not event_div:
                continue
            
            title_elem = event_div.find("h2")
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            
            date_elem = event_div.find("span", id=re.compile(r"event-date-\d+"))
            date_text = date_elem.get_text(strip=True) if date_elem else ""
            
            time_elem = event_div.find("span", id=re.compile(r"event-time-\d+"))
            time_text = time_elem.get_text(strip=True) if time_elem else ""
            
            if not date_text or not time_text:
                continue
            
            event_dt = parse_date_time(date_text, time_text)
            if not event_dt or event_dt.date() != tomorrow:
                continue
            
            # Check for ticket availability
            event_links = li.find_all("a", href=re.compile(r"eventId=\d+"))
            if not event_links:
                continue
            
            has_tickets = False
            ticket_button = None
            
            for link in event_links:
                link_text = link.get_text(strip=True)
                link_title = link.get("title", "")
                
                # Check for German or English indicators
                if ("Platzauswahl" in link_title or 
                    "Weiterleitung zur Platzauswahl" in link_title or
                    link_text in ["Karten", "Restkarten"] or
                    "seat selection" in link_title.lower() or
                    link_text.lower() in ["tickets", "remaining tickets"]):
                    ticket_button = link
                    has_tickets = True
                    break
                
                # If not sold out, assume available
                if ("Ausverkauft" not in link_text and 
                    "Ausverkauft" not in link_title and
                    "sold out" not in link_text.lower() and
                    "sold out" not in link_title.lower()):
                    ticket_button = link
                    has_tickets = True
                    break
            
            if not has_tickets or not ticket_button:
                continue
            
            btn_text = ticket_button.get_text(strip=True)
            href = ticket_button.get("href", "")
            
            # Extract eventId
            event_id = None
            if "eventId=" in href:
                event_id = href.split("eventId=")[1].split("&")[0]
            
            # Build URL
            if href.startswith('/'):
                url = "https://tickets.wiener-staatsoper.at" + href
            elif href.startswith('http'):
                url = href
            else:
                url = STAATSOPER_URL
            
            events_found.append({
                "title": title,
                "date": date_text,
                "time": time_text,
                "datetime": event_dt,
                "status": btn_text,
                "url": url,
                "event_id": event_id
            })
            logging.info(f"Found tickets: {title} at {event_dt.strftime('%H:%M')}")
        
        # Send notification
        if events_found:
            msg = f"<b>🎫 Tickets Available for Tomorrow ({tomorrow_str})!</b>\n\n"
            for ev in events_found:
                msg += f"• <b>{ev['title']}</b>\n"
                msg += f"  📅 {ev['date']} at {ev['time']}\n"
                msg += f"  Status: {ev['status']}\n"
                
                if ev.get('event_id'):
                    available_cats = get_available_categories(driver, ev['event_id'])
                    if available_cats:
                        cat_str = ", ".join(map(str, available_cats))
                        if len(available_cats) == 1:
                            msg += f"  Available Category: {cat_str}\n"
                        else:
                            msg += f"  Available Categories: {cat_str}\n"
                    else:
                        msg += f"  Available Categories: Could not determine\n"
                
                msg += f"  <a href='{ev['url']}'>Buy Tickets Here</a>\n\n"
            
            if send_telegram_message(msg):
                logging.info("Notification sent!")
            else:
                logging.error("Failed to send notification")
        else:
            logging.info(f"No available tickets found for tomorrow ({tomorrow_str}).")
    
    except Exception as e:
        logging.error(f"Error in scraper: {e}", exc_info=True)
    
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logging.warning(f"Error closing WebDriver: {e}")
