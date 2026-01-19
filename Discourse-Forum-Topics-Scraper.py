from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import sqlite3
import re
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
import pymysql  # Use pymysql for MySQL connections

# Connect to the PythonAnywhere MySQL database through the SSH tunnel
conn = pymysql.connect(
    host="YOUR_DB_HOST",
    user="YOUR_DB_USER",
    password="YOUR_DB_PASSWORD",
    database="YOUR_DB_NAME",
    port=3306
)
cursor = conn.cursor()

# Fetch only the "Optimism" DAO name and its forum link from the DAOs table
cursor.execute("SELECT name, forum_link FROM DAOs WHERE name = %s", ("Optimism",))
daos = cursor.fetchall()

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--log-level=3")  # Suppresses most logs except fatal errors

# Initialize the Chrome driver
driver = webdriver.Chrome(options=chrome_options)
action = ActionChains(driver)

processed_links = set()  # To keep track of topics we've already processed

def topic_exists_in_db(topic_link):
    cursor.execute("SELECT views, replies, LastActivityDate FROM ForumLinks WHERE link=%s", (topic_link,))
    result = cursor.fetchone()
    return result

for dao_name, forum_link in daos[0:]:
    # Navigate to the main forum page of the current DAO
    driver.get(forum_link)
    time.sleep(5)

    # Try to detect the type of forum setup
    main_category_elements = driver.find_elements(By.CSS_SELECTOR, ".category-box-heading a.parent-box-link")
    subcategory_elements = driver.find_elements(By.CSS_SELECTOR, ".subcategories a.subcategory")

    if main_category_elements or subcategory_elements:
        main_category_links = [link.get_attribute("href") for link in main_category_elements]
        subcategory_links = [link.get_attribute("href") for link in subcategory_elements]
        category_links = main_category_links + subcategory_links
    else:
        category_links = [link.get_attribute("href") for link in driver.find_elements(By.CSS_SELECTOR, "a.category-title-link")]

    visited_categories = set()

    for category_link in category_links:
        if category_link not in visited_categories:
            driver.get(category_link)
            visited_categories.add(category_link)
            
            last_topic_processed = None
            # Scroll to the bottom to ensure all topics are loaded
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                # Extract topic links, replies, views, and activity, and original posters within the current viewport
                topic_links = driver.find_elements(By.CSS_SELECTOR, ".topic-list-item a.title")
                topic_titles = [topic.text for topic in topic_links]
                replies = driver.find_elements(By.CSS_SELECTOR, ".topic-list-item .posts")
                view_elements = driver.find_elements(By.CSS_SELECTOR, ".topic-list-item .views .number")
                activities = driver.find_elements(By.CSS_SELECTOR, ".topic-list-item .activity a.post-activity span.relative-date")
                original_posters = driver.find_elements(By.CSS_SELECTOR, "img.avatar[title*='Original Poster']")
                original_poster_names = [op.get_attribute("title").split(" - ")[0] for op in original_posters]
                category_names_elements = driver.find_elements(By.CSS_SELECTOR, ".topic-list-item .category-name")
                category_names = [category.text for category in category_names_elements]

                # Extract the parent category name
                try:
                    parent_category_element = driver.find_element(By.CSS_SELECTOR, ".select-kit-selected-name .category-name")
                    parent_category_name = parent_category_element.text
                except NoSuchElementException:
                    try:
                        # New selector for parent category
                        parent_category_element = driver.find_element(By.CSS_SELECTOR, "span.badge-category__name")
                        parent_category_name = parent_category_element.text
                    except NoSuchElementException:
                        print(f"Couldn't find the parent category element for {dao_name}. Skipping to next DAO.")
                        continue

                # Prepend the parent category name to each topic's category name
                category_names = [parent_category_name + " | " + category if category and category != parent_category_name else parent_category_name for category in category_names]

                # Check if the number of extracted category names is less than the number of topic titles
                while len(category_names) < len(topic_titles):
                    category_names.append(parent_category_name)

                all_processed_in_viewport = True

                # Skip topics we've already processed in this session
                if last_topic_processed:
                    index_of_last_processed = [topic.get_attribute('href') for topic in topic_links].index(last_topic_processed)
                    topic_links = topic_links[index_of_last_processed+1:]
                    topic_titles = topic_titles[index_of_last_processed+1:]
                    replies = replies[index_of_last_processed+1:]
                    view_elements = view_elements[index_of_last_processed+1:]
                    activities = activities[index_of_last_processed+1:]
                    original_poster_names = original_poster_names[index_of_last_processed+1:]
                    category_names = category_names[index_of_last_processed+1:]
                
                for title, topic, reply, view, activity, op_name, category_name in zip(topic_titles, topic_links, replies, view_elements, activities, original_poster_names, category_names):
                    topic_link = topic.get_attribute('href')
                    existing_topic = topic_exists_in_db(topic_link)
                    title_attr = view.get_attribute("title")
                    if title_attr:
                        match = re.search(r'(\d+)', title_attr)
                        if match:
                            view_count = match.group(1)
                    else:
                        view_count = view.text

                    timestamp = int(activity.get_attribute("data-time")) / 1000
                    actual_date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

                    if not existing_topic:
                        all_processed_in_viewport = False
                        # Insert the scraped data into the ForumLinks table
                        cursor.execute("INSERT INTO ForumLinks (name, title, link, views, replies, LastActivityDate, OriginalPoster, Category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                       (dao_name, title, topic_link, view_count, reply.text, actual_date, op_name, category_name))
                        conn.commit()
                    else:
                        existing_views, existing_replies, existing_date = existing_topic
                        if int(view_count) != int(existing_views) or int(reply.text) != int(existing_replies) or actual_date != existing_date:
                            all_processed_in_viewport = False
                            # Update the existing record in the ForumLinks table
                            cursor.execute("UPDATE ForumLinks SET views=%s, replies=%s, LastActivityDate=%s, OriginalPoster=%s, Category=%s WHERE link=%s",
                                           (view_count, reply.text, actual_date, op_name, category_name, topic_link))
                            conn.commit()

                    processed_links.add(topic_link)
                    last_topic_processed = topic_link

                # Scroll down
                    driver.execute_script("window.scrollBy(0, 1000);")  # Scroll down by 1000 pixels
                time.sleep(5)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                # If the height hasn't changed, we've reached the bottom
                if new_height == last_height:
                    break
                last_height = new_height

# Close the browser and the database connection
driver.quit()
conn.close()
