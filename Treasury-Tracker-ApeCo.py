import os
from decimal import Decimal, InvalidOperation
import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Wallet information (public DAO treasury wallets)
wallets = {
    "317 Wallet": "0x3b319def689f90f9dc406c163434df31b06d0fc2",
    "Small Grants Ops": "0x8b32d9b097cbff1a11ff60ffa750cc504989550e",
    "OC Wallet": "0x613db2397725d9e532b85d370f3eb6e92aa888a6",
    "Small Grants Vault": "0x61c0d1a4b1f1818bc6d14ab208d2b0999df5e862",
    "Delegation C1": "0xd7d32a4540a6d4ce54fb3a515055bf1e08170abc",
    "Delegation Master": "0x2efddacf97cb6aa72e8fd481c3b0818bc1985af4",
    "FAC Initiative": "0x2136d9bb81a20fc8923f7e84d0653d83d983e02b",
    "Defi Wallet": "0x63d8d8ef8a4cc44df7da14636142dcf23c586c8b",
    "GWG Daily Ops": "0xf1d4e00e202e0a36e6f7338c33bcb268d91b6232",
    "408 Main": "0xa9b6808f807c8a93b186f0dce2cfa5d941bd0382",
}

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--log-level=3")  # Suppresses most logs except fatal errors

# Initialize the Chrome driver
driver = webdriver.Chrome(options=chrome_options)

# Connect to MySQL database (via SSH tunnel in real deployment)
conn = mysql.connector.connect(
    host='127.0.0.1',      # Localhost due to SSH tunnel
    user='YOUR_DB_USER',   # Replace with your DB username
    password='YOUR_DB_PASSWORD',   # Replace with your DB password
    database='YOUR_DB_NAME',       # Replace with your DB name
    port=3306              # Example default port (use yours if needed)
)
cursor = conn.cursor()

# Create a single table for all data with a primary key
cursor.execute('''
    CREATE TABLE IF NOT EXISTS ApeCoinData (
        id INT AUTO_INCREMENT PRIMARY KEY,
        wallet_name VARCHAR(255) NOT NULL,
        wallet_address VARCHAR(255) NOT NULL,
        token_name VARCHAR(255),
        token_price DECIMAL(20,8),
        token_amount DECIMAL(20,8),
        usd_value DECIMAL(20,2),
        staking_pool VARCHAR(255),
        staked_balance DECIMAL(30,10),
        staked_rewards DECIMAL(20,8),
        staked_usd_value DECIMAL(20,2),
        UNIQUE(wallet_name, wallet_address)
    )
''')

# Base URL
base_url = "https://debank.com/profile/"

# Utility function to safely parse a string to Decimal with specified precision
def parse_decimal(value, decimal_places):
    if value is None:
        return None
    try:
        quantize_str = '1.' + '0' * decimal_places

        # Handle special cases like $0.0₅4025
        value = value.replace('₅', '00001')

        return Decimal(value).quantize(Decimal(quantize_str))
    except (InvalidOperation, TypeError):
        return None

# Function 1: Scrape general wallet data + staked values + rewards
def scrape_wallet_and_stake_data(wallet_name, wallet_address):
    driver.get(base_url + wallet_address)
    time.sleep(5)  # Wait for the page to load

    # Scrape general wallet data
    tokens = driver.find_elements(By.CSS_SELECTOR, "a.TokenWallet_detailLink__goYJR")
    price_elements = driver.find_elements(By.XPATH, "//div[@class='db-table-cell' and contains(text(), '$')]")
    amount_elements = driver.find_elements(By.XPATH, "//div[@class='db-table-cell'][3]")
    usd_values = driver.find_elements(By.CSS_SELECTOR, "div.db-table-cell.is-right[style='width: 20%;']")

    # Initialize with NULL values
    token_name, token_price, token_amount, usd_value = None, None, None, None

    if tokens:
        token_name = tokens[0].text
    if price_elements:
        token_price = parse_decimal(price_elements[0].text.replace("$", "").replace(",", ""), 8)
    if amount_elements:
        token_amount = parse_decimal(amount_elements[0].text.replace(",", ""), 8)
    if usd_values:
        usd_value = parse_decimal(usd_values[0].text.replace("$", "").replace(",", ""), 2)

    # Scrape staked balance, rewards, etc.
    balance_elements = driver.find_elements(By.XPATH, "//div[@class='Panel_card__1vXt+']//div[contains(@style,'margin-top')]")
    usd_value_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '$')]")
    pool_elements = driver.find_elements(By.XPATH, "//a[contains(@href, '/token/eth/0x4d224452801aced8b2f0aebe155379bb5d594381')]")

    staking_pool = pool_elements[0].text if pool_elements else None
    staked_balance = None
    if balance_elements:
        raw_staked_balance = balance_elements[0].text.replace(",", "").replace("APE", "").strip()
        staked_balance = parse_decimal(raw_staked_balance, 10)

    staked_usd_value = parse_decimal(usd_value_elements[0].text.replace("$", "").replace(",", ""), 2) if usd_value_elements else None

    rewards_elements = driver.find_elements(By.XPATH, "//div[contains(@style,'margin-top')]")
    staked_rewards = parse_decimal(rewards_elements[1].text.split()[0].replace(",", ""), 8) if len(rewards_elements) > 1 else None

    # Insert or update data in MySQL
    cursor.execute('''
        INSERT INTO ApeCoinData (
            wallet_name, wallet_address, token_name, token_price, token_amount, usd_value,
            staking_pool, staked_balance, staked_rewards, staked_usd_value
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            token_name = VALUES(token_name),
            token_price = VALUES(token_price),
            token_amount = VALUES(token_amount),
            usd_value = VALUES(usd_value),
            staking_pool = VALUES(staking_pool),
            staked_balance = VALUES(staked_balance),
            staked_rewards = VALUES(staked_rewards),
            staked_usd_value = VALUES(staked_usd_value)
    ''', (
        wallet_name, wallet_address, token_name, token_price, token_amount, usd_value,
        staking_pool, staked_balance, staked_rewards, staked_usd_value
    ))

# Main execution loop
for name, address in wallets.items():
    print(f"\nProcessing wallet: {name}")
    scrape_wallet_and_stake_data(name, address)

# Commit + close
conn.commit()
conn.close()
driver.quit()
