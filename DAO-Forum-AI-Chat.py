import mysql.connector
import openai

def execute_query(query, params=None):
    """
    Execute SQL query and return results.
    """
    # Database connection parameters
    DB_NAME = 'YOUR_DB_NAME'
    DB_USER = 'YOUR_DB_USER'
    DB_PASSWORD = 'YOUR_DB_PASSWORD'
    DB_HOST = 'YOUR_DB_HOST'
    DB_PORT = 3306  # default or placeholder

    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

def generate_response_for_data(data, username):
    """
    Uses ChatGPT to generate a natural language response based on the data.
    Processes data in smaller chunks to avoid exceeding context length limits.
    """
    client = openai.OpenAI(api_key='YOUR_OPENAI_API_KEY')
    if not data:
        prompt = f"No relevant data found for the user '{username}'. Please refine your question or ask about someone else."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "assistant", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    else:
        # Implement finer chunking
        max_chars_per_chunk = 2000  # Maximum characters per chunk, adjust as needed
        chunks = []
        current_chunk = ""
        for row in data:
            row_str = str(row)
            if len(current_chunk) + len(row_str) + 2 > max_chars_per_chunk:
                chunks.append(current_chunk)
                current_chunk = row_str
            else:
                if current_chunk:
                    current_chunk += "\n" + row_str
                else:
                    current_chunk = row_str
        if current_chunk:
            chunks.append(current_chunk)

        responses = []
        for chunk in chunks:
            prompt = (
                f"Based solely on the following data about the user '{username}', provide a very concise, yet detailed summary of their specific contributions to the Rari Foundation. "
                f"Include any working groups, roles, proposals, discussions, or actions they have been involved in as mentioned in the data. "
                f"Focus on exact details and avoid general compliments or statements not supported by the data. "
                f"Present the information in a concise paragraph, limited to 3 sentences."
                f"\n\nData:\n{chunk}"
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "assistant", "content": prompt}
                ]
            )
            responses.append(response.choices[0].message.content.strip())

        # Combine the responses
        combined_response = ' '.join(responses)
        # Optionally, summarize the combined response if it's too long
        if len(combined_response) > 1500:  # Adjust the length as needed
            final_prompt = (
                f"Summarize the following text into a concise paragraph about '{username}', focusing on their specific contributions to the Rari Foundation DAO, roles, and actions mentioned. "
                f"Avoid any general statements not supported by the data.\n\n{combined_response}"
            )
            final_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "assistant", "content": final_prompt}
                ]
            )
            return final_response.choices[0].message.content.strip()
        else:
            return combined_response

def extract_username(user_input):
    """
    Extracts the username from the user input.
    """
    user_input_lower = user_input.lower()
    if 'who is' in user_input_lower:
        idx = user_input_lower.find('who is')
        username = user_input[idx + len('who is'):].strip(' ?')
        return username.strip()
    else:
        # Return the entire input if 'who is' not found
        return user_input.strip()

def interact_with_chatgpt():
    """
    Interacts with the user, dynamically querying the database and using ChatGPT for responses.
    """
    print("Ask me anything about the database or type 'quit' to exit:")

    while True:
        user_input = input("> ")
        if user_input.lower() == 'quit':
            break

        username = extract_username(user_input)
        if username:
            dao_name_filter = 'Rari Foundation'  # DAO name filter
            # Updated SQL query to include DAO name filter
            sql_query = "SELECT * FROM ForumPosts WHERE LOWER(author) = LOWER(%s) AND LOWER(dao_name) = LOWER(%s)"
            params = (username, dao_name_filter)
            results = execute_query(sql_query, params)
            response = generate_response_for_data(results, username)
        else:
            response = "I could not generate a specific query from your question. Please be more specific."

        print("Answer:", response)

if __name__ == "__main__":
    interact_with_chatgpt()
