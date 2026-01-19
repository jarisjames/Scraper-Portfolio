from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from selenium.common.exceptions import NoSuchElementException
import json
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementNotInteractableException
from datetime import datetime
import subprocess
from bs4 import BeautifulSoup
import emoji 
import sqlite3
import hashlib
import re

def format_post_time(post_time_element):
    try:
        post_time_str = post_time_element.get_attribute('title')
        # Parse the date string into a datetime object
        post_time_obj = datetime.strptime(post_time_str, '%b %d, %Y %I:%M %p')
        # Format the datetime object into the desired string format
        formatted_post_time = post_time_obj.strftime('%Y-%m-%d %I:%M %p')
    except ValueError:
        formatted_post_time = "Unknown Time"
    return formatted_post_time

def post_exists(cursor, post_identifier):
    cursor.execute("SELECT PostID, dao_name, author, role, content, post_time, total_likes, likes, replies, repliers, post_links, link_clicks, links, images, title, post_identifier FROM ForumPosts WHERE post_identifier=?", (post_identifier,))
    return cursor.fetchone()

def update_post(cursor, post_data, post_identifier):
    cursor.execute("""
        UPDATE ForumPosts 
        SET dao_name=?, author=?, content=?, likes=?, post_time=?, total_likes=?, images=?, role=?, links=?, replies=?, repliers=?, TotalReplies=?, post_links=?, link_clicks=?
        WHERE post_identifier=?
    """, (*post_data, post_identifier))

def deep_tuple(lst):
    if isinstance(lst, (list, tuple)):
        return tuple(deep_tuple(x) for x in lst)
    else:
        return lst
    
def generate_post_identifier(author, post_time, title, content):
    # Remove all integers from content
    content_without_integers = re.sub(r'\d+', '', content)
    
    # Define the size of the chunks you want to take: beginning, middle, end
    chunk_size = max(int(len(content_without_integers) * 0.1), 1)  # 10% of content or at least 1 char
    
    # Take the first 10% of the content without integers for hashing
    beginning_chunk = content_without_integers[:chunk_size]
    
    # Take the middle 10% of the content without integers for hashing
    middle_index = len(content_without_integers) // 2
    middle_chunk = content_without_integers[middle_index:middle_index + chunk_size]
    
    # Take the last 10% of the content without integers for hashing
    end_chunk = content_without_integers[-chunk_size:]
    
    # Combine author, post_time, title, and the three chunks to create a unique string for hashing
    combined_string = author + post_time + title + beginning_chunk + middle_chunk + end_chunk
    
    # Encode the string to bytes
    encoded_string = combined_string.encode('utf-8')
    
    # Generate the SHA-256 hash
    sha256_hash = hashlib.sha256(encoded_string).hexdigest()
    
    return sha256_hash

def extract_and_replace_emojis(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all emoji image tags and replace them with their text representation
    for emoji_tag in soup.find_all('img', {'class': 'emoji'}):
        emoji_text = emoji_tag.get('title', '')
        if emoji_text:
            emoji_tag.replace_with(emoji_text)

    # Extract text after emoji replacement
    text = soup.get_text()

    # Add spaces between concatenated words and numbers
    formatted_text = re.sub(r'(\D)(\d)', r'\1 \2', text)  # Add space between non-digit and digit
    formatted_text = re.sub(r'(\d)(\D)', r'\1 \2', formatted_text)  # Add space between digit and non-digit

    return formatted_text

# Function to scrape Link Clicks for a given post element
def scrape_link_clicks_for_post(post_element):
    link_clicks = []
    try:
        link_click_elements = post_element.find_elements(By.XPATH, './/a[span[@class="badge badge-notification clicks"]]')
        for link_element in link_click_elements:
            link_url = link_element.get_attribute('href')
            link_title = link_element.text.strip()
            click_count_element = link_element.find_element(By.XPATH, './/span[@class="badge badge-notification clicks"]')
            click_count = click_count_element.text
            link_clicks.append((link_title, link_url, click_count))
    except NoSuchElementException:
        pass
    return link_clicks

# Function to scrape likes for a given post element
def scrape_likes_for_post(post_element):
    likes = []
    try:
        ens_likes_element = post_element.find_elements(By.CSS_SELECTOR, 'div.only-like.discourse-reactions-counter')
        bankless_likes_element = post_element.find_elements(By.CSS_SELECTOR, 'button.like-count')
        
        if ens_likes_element:
            ens_likes_element[0].click()
            time.sleep(2)
            
            # Check for the "show-users" button and click it if it exists
            try:
                expand_button = post_element.find_element(By.CSS_SELECTOR, 'button.show-users')
                expand_button.click()
                time.sleep(2)  # Wait for additional likers to load
            except NoSuchElementException:
                pass  # Continue if the "show-users" button doesn't exist
            
            likes_elements = post_element.find_elements(By.CSS_SELECTOR, ".discourse-reactions-state-panel-reaction .trigger-user-card")
            for liker in likes_elements:
                likes.append(liker.get_attribute('data-user-card'))
        elif bankless_likes_element:
            bankless_likes_element[0].click()
            time.sleep(2)
            likes_elements = post_element.find_elements(By.CSS_SELECTOR, ".who-liked .trigger-user-card")
            for liker in likes_elements:
                likes.append(liker.get_attribute('href').split('/')[-1])
        
        driver.find_element(By.CSS_SELECTOR, ".d-modal-backdrop").click()
        time.sleep(1)
    except:
        pass
    return likes

# Function to scrape total likes for a given post element
def scrape_total_likes_for_post(post_element, individual_likes, has_emoji_reactions):
    # If the post has emoji reactions, return 0 for total likes
    if has_emoji_reactions:
        return 0

    try:
        # Handle ENS likes
        ens_likes_element = post_element.find_elements(By.CSS_SELECTOR, 'span.reactions-counter')
        if ens_likes_element:
            # Use the count of individual likes for total likes
            total_likes = len(individual_likes.split(','))
            return total_likes

        # Handle Bankless likes
        bankless_likes_element = post_element.find_elements(By.CSS_SELECTOR, 'button.like-count')
        if bankless_likes_element:
            total_likes = int(bankless_likes_element[0].text.strip())
            return total_likes

        return 0
    except:
        return 0

    
# Function to scrape replies for a given post element
def scrape_replies_for_post(post_element):
    replies = []
    repliers = []  # List to store usernames of those who replied
    try:
        # Find the reply button specifically in the reply section at the bottom of the post
        reply_button = post_element.find_element(By.XPATH, './/button[contains(@class, "show-replies")]')
        
        # Debugging: Print the element that is about to be clicked
        print(f"Debugging: About to click the following element: {reply_button.get_attribute('outerHTML')}")
        
        # Use ActionChains to move to the element and click it
        actions = ActionChains(driver)
        actions.move_to_element(reply_button).click().perform()
        
        time.sleep(2)  # Wait for replies to load

        # Scrape the content of each reply
        reply_elements = post_element.find_elements(By.CSS_SELECTOR, '.reply')
        for reply in reply_elements:
            reply_content = reply.find_element(By.CSS_SELECTOR, '.cooked').text
            reply_author = reply.find_element(By.CSS_SELECTOR, '.names .username').text
            replies.append((reply_author, reply_content))
            repliers.append(reply_author)  # Add the username to the repliers list

        time.sleep(1)
    except NoSuchElementException:
        print("Debugging: NoSuchElementException encountered.")
        pass
    except TimeoutException:
        print("Timed out waiting for page to load.")
    return replies, repliers  # Return both the replies and the list of repliers

# Function to scrape post links for a given post element
def scrape_post_links_for_post(post_element):
    post_links = []
    try:
        post_links_elements = post_element.find_elements(By.CSS_SELECTOR, 'ul.post-links li a.track-link.inbound')
        for link_element in post_links_elements:
            link = link_element.get_attribute('href')
            text_html = link_element.get_attribute('innerHTML')
            text = extract_and_replace_emojis(text_html)  # Use the function to replace emoji images with text
            post_links.append({'link': link, 'text': text})
    except NoSuchElementException:
        pass
    return post_links

# Function to scrape images for a given post element
def scrape_images_for_post(post_element):
    images = []
    try:
        image_elements = post_element.find_elements(By.CSS_SELECTOR, '.cooked img')
        for image in image_elements:
            images.append(image.get_attribute('src'))
    except:
        pass
    return images

# Function to scrape links for a given post element
def scrape_links_for_post(post_element):
    links = []
    try:
        link_elements = post_element.find_elements(By.CSS_SELECTOR, '.cooked a')
        for link in link_elements:
            links.append(link.get_attribute('href'))
    except NoSuchElementException:
        pass
    return links

# Function to scrape roles for a given post element
def scrape_role_for_post(post_element):
    text_role = None  # Default value
    svg_role = None  # Default value
    user_title_role = None  # Default value

    # Try to find the SVG role
    try:
        svg_role_element = post_element.find_element(By.CSS_SELECTOR, 'span.svg-icon-title')
        svg_role = svg_role_element.get_attribute('title')
        if svg_role == "expand/collapse":
            svg_role = None
    except NoSuchElementException:
        pass

    # Try to find the text-based role
    try:
        role_element = post_element.find_element(By.CSS_SELECTOR, 'a.user-group')
        text_role = role_element.text
    except NoSuchElementException:
        pass

    # Try to find the user title role
    try:
        user_title_role_element = post_element.find_element(By.CSS_SELECTOR, 'span.user-title')
        user_title_role = user_title_role_element.text
    except NoSuchElementException:
        pass

    # Combine roles if multiple are present
    roles = set()  # Using a set to automatically remove duplicates
    if text_role:
        roles.add(text_role)
    if svg_role:
        roles.add(svg_role)
    if user_title_role:
        roles.add(user_title_role)

    return ', '.join(roles) if roles else "No Role"

# Function to scrape emoji reactions for a given post element
def scrape_emoji_reactions_for_post(post_element):
    emoji_reactions = {}
    try:
        # Find the total number of emoji reactions
        total_reactions_counter = post_element.find_element(By.CSS_SELECTOR, '.discourse-reactions-counter .reactions-counter')
        
        # Use ActionChains to move to the element and click it
        actions = ActionChains(driver)
        actions.move_to_element(total_reactions_counter).click().perform()
        time.sleep(2)

        # Scrape the list of emojis and usernames with hovering
        emoji_list_elements = post_element.find_elements(By.CSS_SELECTOR, '.discourse-reactions-list-emoji')
        
        # Process only the first 3 emojis displayed, ignoring any additional emojis
        for emoji_element in emoji_list_elements[:3]:  # Only consider the first 3 emoji elements
            emoji_type = emoji_element.find_element(By.CSS_SELECTOR, 'img.emoji').get_attribute('alt')
            
            # Hover over each emoji to reveal the usernames
            actions = ActionChains(driver)
            actions.move_to_element(emoji_element).perform()
            time.sleep(2)  # Wait for usernames to load
            
            # Update the CSS selector to accurately capture usernames
            usernames_elements = emoji_element.find_elements(By.CSS_SELECTOR, '.username')
            usernames = [user.text for user in usernames_elements if user.text]  # Ensure non-empty usernames are added
            
            if usernames:
                emoji_reactions[emoji_type] = usernames

        # Close the emoji reaction panel
        driver.find_element(By.CSS_SELECTOR, ".d-modal-backdrop").click()
        time.sleep(1)
    except NoSuchElementException:
        pass
    except TimeoutException:
        print("Timed out waiting for page to load.")
    except ElementNotInteractableException:
        print("Element not interactable. Skipping this emoji.")

    # Format the emoji reactions for better readability
    formatted_emoji_reactions = ', '.join([f"{emoji}-{len(users)} reactions ({', '.join(users)})" for emoji, users in emoji_reactions.items() if users])
    total_emoji_reactions = sum(len(users) for users in emoji_reactions.values())
    
    # Return null if there are no reactions
    return (formatted_emoji_reactions if formatted_emoji_reactions else None, total_emoji_reactions)

# Function to scroll through a page incrementally and scrape data
def scroll_and_scrape():
    post_data_set = set()
    unique_posts = set()
    no_new_posts_counter = 0  # Counter to track consecutive reloads with no new posts
    clicked_results_posts = set()

    while True:
        all_posts = driver.find_elements(By.CSS_SELECTOR, ".topic-post")
        new_posts_in_this_iteration = 0  # Counter to track new posts in the current iteration

        for selenium_post in all_posts:
            try:
                post_content_html = selenium_post.find_element(By.CSS_SELECTOR, '.cooked').get_attribute('innerHTML')
                content = extract_and_replace_emojis(post_content_html)
            except NoSuchElementException:
                continue

            try:
                author = selenium_post.find_element(By.CSS_SELECTOR, '.names .username').text
            except NoSuchElementException:
                author = "Unknown Author"

            try:
                post_time_element = selenium_post.find_element(By.CSS_SELECTOR, '.relative-date')
                post_time = format_post_time(post_time_element)  # This sets the 'post_time' variable
            except NoSuchElementException:
                post_time = "Unknown Time"

            # Create a unique identifier for each post based on its author and post_time
            post_identifier = generate_post_identifier(author, post_time, title, content)

            # Debugging: Print the unique identifier for each post
            print(f"Debugging: Post Identifier: {post_identifier}")


            # Initialize has_emoji_reactions to False for each post
            has_emoji_reactions = False

            # Check if this post is unique
            if post_identifier not in unique_posts:
                new_posts_in_this_iteration += 1
                unique_posts.add(post_identifier)

                likes = scrape_likes_for_post(selenium_post)
                likes_string = ','.join(likes)

                # Scrape emoji reactions (insert this line here)
                emoji_reactions, total_emoji_reactions = scrape_emoji_reactions_for_post(selenium_post)
                has_emoji_reactions = total_emoji_reactions > 0

                total_likes = scrape_total_likes_for_post(selenium_post, likes_string, has_emoji_reactions)
                post_links = scrape_post_links_for_post(selenium_post)
                images = scrape_images_for_post(selenium_post)
                links = scrape_links_for_post(selenium_post)
                role = scrape_role_for_post(selenium_post)
                replies, repliers = scrape_replies_for_post(selenium_post)
                print(f"Repliers: {', '.join(repliers)}")
                link_clicks = scrape_link_clicks_for_post(selenium_post)

                # Add scraped data to the post_data_set
                post_data_set.add((author, content, tuple(likes), post_time, total_likes, tuple(images), role, tuple(links), tuple(replies), tuple(repliers), json.dumps(post_links), tuple(link_clicks), emoji_reactions, total_emoji_reactions))


        print(f"New posts in this iteration: {new_posts_in_this_iteration}")

        if new_posts_in_this_iteration == 0:
            no_new_posts_counter += 1
        else:
            no_new_posts_counter = 0  # Reset the counter if new posts are found

        if no_new_posts_counter >= 3:  # Stop if no new posts are found in 3 consecutive iterations
            print("No new posts found in 3 consecutive iterations. Exiting.")
            break

        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(3)

    return list(post_data_set)

# Set Chrome options
chrome_options = Options()
chrome_options.add_argument("--log-level=3")  # Suppresses most logs except fatal errors

# Connect to the SQLite database
conn = sqlite3.connect("YOUR_DB_PATH_HERE")
cursor = conn.cursor()

# Fetch the DAO names, forum links, and titles from the ForumLinks table
cursor.execute("SELECT name, link, title FROM ForumLinks")
forum_links_data = cursor.fetchall()

# Initialize the Chrome driver
driver = webdriver.Chrome(options=chrome_options)

# Fetch the DAO names, forum links, and titles from the ForumLinks table WHERE name = 'ENS'
cursor.execute("SELECT name, link, title FROM ForumLinks WHERE name = ?", ("ENS",))
forum_links_data = cursor.fetchall()

# Assuming forum_links_data contains only entries for 'Optimism', iterate through it directly
for dao_name, link, title in forum_links_data:
    print(f"Scraping posts for DAO: {dao_name} with title: {title}")
    # Navigate to the current forum link
    driver.get(link)
    # The rest of your scraping logic follows


    # Navigate to the current forum link
    driver.get(link)

    # Let's give the page some time to load
    time.sleep(5)

    # Scroll through the topic incrementally and scrape the data
    post_data = scroll_and_scrape()

    # Find the earliest post_time for the current title
    earliest_post_time = min(post_data, key=lambda x: datetime.strptime(x[3], '%Y-%m-%d %I:%M %p'))[3] if post_data else None

    if earliest_post_time:
        # Update the Created column in the ForumLinks table for the current title
        cursor.execute("""
            UPDATE ForumLinks
            SET Created = ?
            WHERE title = ?
        """, (earliest_post_time, title))
        conn.commit()
        print(f"Updated 'Created' column for title '{title}' with earliest post time: {earliest_post_time}")

    # Sort posts by number of likes and enumerate the output
    sorted_posts = sorted(post_data, key=lambda x: len(x[2]), reverse=True)

    # Inside the loop where you process each post:
    for index, (author, content, likes, post_time, total_likes, images, role, links, replies, repliers, post_links, link_clicks, emoji_reactions, total_emoji_reactions) in enumerate(sorted_posts, start=1):
    # ... existing code ...
        TotalReplies = len(repliers)  # Calculate the total number of repliers
        likes = [like for like in likes if like is not None]
        images = [image for image in images if image is not None]
        links = [link for link in links if link is not None]

        # Create a unique identifier for each post based on its content and author
        post_identifier = generate_post_identifier(author, post_time, title, content)

        # Check if the post already exists in the database
        existing_post = post_exists(cursor, post_identifier)
        if existing_post:
            existing_PostID, existing_name, existing_author, existing_Role, existing_content, existing_post_time, existing_total_likes, existing_likes, existing_replies, existing_Repliers, existing_post_links, existing_link_clicks, existing_Links, existing_Images, existing_title, existing_post_identifier = existing_post
            
            # Logging for debugging
            print(f"Existing post identifier: {existing_post_identifier}")
            print(f"New post identifier: {post_identifier}")
            print(f"Post content: {content[:100]}...")  # Print the first 100 characters of the content
            
            if (existing_author != author or 
                existing_content != content or 
                set(existing_likes.split(',')) != set(likes) or 
                set(existing_replies.split(',')) != set(replies) or 
                set(existing_Repliers.split(',')) != set(repliers)):
                

                update_post(cursor, (dao_name, author, content, ','.join(likes), post_time, total_likes, ','.join(images), role, ','.join(links), str(replies), ','.join(repliers), TotalReplies, json.dumps(post_links), str(link_clicks)), post_identifier)
                print(f"Post by {author} has been updated in the database.")
            else:
                print(f"Post by {author} already exists in the database with the same data. Skipping...")
                continue

        else:
            # Insert the scraped data into the ForumPosts table
            cursor.execute("""
                INSERT INTO ForumPosts (dao_name, post_identifier, author, content, likes, post_time, total_likes, images, role, links, replies, repliers, TotalReplies, post_links, link_clicks, emoji_reactions, TotalEmojiReactions, title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (dao_name, post_identifier, author, content, ','.join(likes), post_time, total_likes, ','.join(images), role, ','.join(links), str(replies), ','.join(repliers), TotalReplies, json.dumps(post_links), str(link_clicks), emoji_reactions, total_emoji_reactions, title))

        print(f"{index}. Post by {author} (Role: {role}):\nTitle: {title}\n{content}\nHas {total_likes} total likes and {len(likes)} individual likes: {', '.join(likes)}\nPosted at: {post_time}\nImages: {', '.join(images)}\nLinks: {', '.join(links)}\nReplies: {replies}\nTotalReplies: {TotalReplies}\nRepliers: {', '.join(repliers)}\nPost Links: {json.loads(post_links)}\n{'-'*50}")
        print(f"Link Clicks: {link_clicks}\n{'-'*50}")



        # Commit the changes to the database
        conn.commit()
    
        print(f"{index}. Post by {author} (Role: {role}):\n{content}\nHas {total_likes} total likes and {len(likes)} individual likes: {', '.join(likes)}\nPosted at: {post_time}\nImages: {', '.join(images)}\nLinks: {', '.join(links)}\nReplies: {replies}\nTotalReplies: {TotalReplies}\nRepliers: {', '.join(repliers)}\nPost Links: {json.loads(post_links)}\n{'-'*50}")
        print(f"Link Clicks: {link_clicks}\n{'-'*50}")


# Close the browser
driver.quit()