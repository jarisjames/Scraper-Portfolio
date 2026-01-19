from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup

def scrape_and_print_data():
    time.sleep(3)
    voter_anchors = driver.find_elements(By.XPATH, '//a[contains(@href, "/delegate/")]')
    print(f"Found {len(voter_anchors)} raw voter blocks")
    seen_wallets = set()
    count = 0

    for anchor in voter_anchors:
        try:
            wallet = anchor.get_attribute('href').split('/')[-1]
            if wallet in seen_wallets:
                continue
            seen_wallets.add(wallet)

            voter_name = anchor.text.strip()
            # Use the table row (ancestor <tr>) as the container.
            wrapper_div = anchor.find_element(By.XPATH, './ancestor::tr')
            numeric_p_tags = wrapper_div.find_elements(By.XPATH, './/p[contains(@class,"chakra-text css-1l4y9xb")]')
            
            # Initialize fields
            raw_votes = "Unknown"
            percent = "Unknown"
            
            # If the first element is the delegate's name, shift indices
            if len(numeric_p_tags) >= 3 and numeric_p_tags[0].text.strip() == voter_name:
                raw_votes = numeric_p_tags[1].text.strip()
                percent = numeric_p_tags[2].text.strip()
            elif len(numeric_p_tags) >= 2:
                raw_votes = numeric_p_tags[0].text.strip()
                percent = numeric_p_tags[1].text.strip()

            # Vote direction: try the three possible CSS classes.
            try:
                vote_direction_elem = wrapper_div.find_element(By.XPATH, './/p[contains(@class,"chakra-text css-1xb8z7d")]')
                vote_direction = vote_direction_elem.text.strip()
            except Exception:
                try:
                    vote_direction_elem = wrapper_div.find_element(By.XPATH, './/p[contains(@class,"chakra-text css-5inndu")]')
                    vote_direction = vote_direction_elem.text.strip()
                except Exception:
                    try:
                        vote_direction_elem = wrapper_div.find_element(By.XPATH, './/p[contains(@class,"chakra-text css-1xgz4y8")]')
                        vote_direction = vote_direction_elem.text.strip()
                    except Exception:
                        vote_direction = "Unknown"

            count += 1
            print(f"{count}. Wallet: {wallet}, Name: {voter_name}, Voting Power: {raw_votes}, Voting Power %: {percent}, Vote Direction: {vote_direction}")
        except Exception as e:
            print(f"Error processing a voter: {e}")
            continue

def get_proposal_status():
    try:
        if driver.find_element(By.CSS_SELECTOR, 'button.chakra-button.css-1ydcfsc'):
            return "Pending Queue"
    except:
        pass
    try:
        if driver.find_element(By.CSS_SELECTOR, 'p.chakra-text.css-1wi275w'):
            return "Executed"
    except:
        pass
    try:
        if driver.find_element(By.CSS_SELECTOR, 'p.chakra-text.css-19opcjo'):
            text = driver.find_element(By.CSS_SELECTOR, 'p.chakra-text.css-19opcjo').text
            if text == "Quorum not reached":
                return "Defeated (Quorum Not Reached)"
            elif text == "Cancelled":
                return "Canceled"
            elif text == "Proposal defeated":
                return "Defeated"
    except:
        pass
    try:
        if driver.find_element(By.CSS_SELECTOR, 'button.chakra-button.css-jttdss'):
            return "Active"
    except:
        pass
    return "Unknown"

def get_additional_data():
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    def safe_find(text):
        try:
            return soup.find('p', text=text).find_next('p').text
        except:
            return "Unknown"

    quorum = safe_find('Quorum')
    majority_support = safe_find('Majority support')
    for_value = safe_find('For')
    against_value = safe_find('Against')
    abstain_value = safe_find('Abstain')
    return quorum, majority_support, for_value, against_value, abstain_value

chrome_options = Options()
chrome_options.add_argument("--log-level=3")
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.tally.xyz/gov/rari-foundation/proposals")
time.sleep(5)

try:
    cookie_consent_button = driver.find_element(By.CSS_SELECTOR, ".CookieConsent button")
    cookie_consent_button.click()
    time.sleep(2)
except:
    pass

visited_proposals = set()
proposal_index = 0

while True:
    proposals = driver.find_elements(By.CSS_SELECTOR, "td.css-1dsv5rv a.chakra-link")
    proposal_urls = [proposal.get_attribute('href') for proposal in proposals]

    if proposal_index >= len(proposal_urls):
        try:
            load_more_proposals_button = driver.find_element(By.XPATH, '//button[text()="Load more"]')
            load_more_proposals_button.click()
            time.sleep(10)
            new_proposals = driver.find_elements(By.CSS_SELECTOR, "td.css-1dsv5rv a.chakra-link")
            if len(new_proposals) == len(proposals):
                driver.close()
                break
            proposal_index = 0
            continue
        except:
            break

    if proposal_urls[proposal_index] in visited_proposals:
        proposal_index += 1
        continue

    visited_proposals.add(proposal_urls[proposal_index])
    proposals[proposal_index].click()
    time.sleep(5)

    list_button = driver.find_element(By.CSS_SELECTOR, 'button[id*="tab-2"].chakra-tabs__tab')
    list_button.click()
    time.sleep(5)

    proposal_title_element = driver.find_element(By.CSS_SELECTOR, 'h3.chakra-text.css-1i5nimd')
    proposal_title = proposal_title_element.text

    proposal_url = proposal_urls[proposal_index]  
    print(f"\nProposal Title: {proposal_title}")
    print(f"Proposal URL: {proposal_url}")

    try:
        author_link = driver.find_element(By.XPATH, '//a[contains(@href, "/delegate/") and contains(@href, "0x")]')
        author_wallet = author_link.get_attribute('href').split('/')[-1]
    except:
        author_wallet = "Unknown"
    print(f"Author Wallet: {author_wallet}")

    date_element = driver.find_element(By.XPATH, '//p[contains(text(), "Proposed on:")]')
    date_published = date_element.text.replace("Proposed on: ", "")
    print(f"Date Published: {date_published}")

    status = get_proposal_status()
    print(f"Status: {status}")

    quorum, majority_support, for_value, against_value, abstain_value = get_additional_data()
    print(f"Quorum: {quorum}")
    print(f"Majority Support: {majority_support}")
    print(f"For: {for_value}")
    print(f"Against: {against_value}")
    print(f"Abstain: {abstain_value}")

    list_button = driver.find_element(By.CSS_SELECTOR, 'button[id*="tab-2"].chakra-tabs__tab')
    list_button.click()

    try:
        time.sleep(2)
        view_all_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "/votes") and .//button[contains(text(), "View all")]]'))
        )
        view_all_href = view_all_link.get_attribute("href")
        driver.get(view_all_href)
        time.sleep(5)
    except Exception as e:
        print("Could not follow 'View all' link:", e)
        with open("failed_view_all.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    scrape_and_print_data()

    while True:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            load_more_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//button[text()="Load more"]'))
            )
            ActionChains(driver).move_to_element(load_more_button).click(load_more_button).perform()
            time.sleep(5)
            scrape_and_print_data()
        except:
            break

    driver.get("https://www.tally.xyz/gov/rari-foundation/proposals")
    time.sleep(5)
    proposal_index += 1

try:
    driver.quit()
except:
    pass
