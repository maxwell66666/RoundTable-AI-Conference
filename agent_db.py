import sqlite3
import json
import random
from functools import wraps

# Database connection decorator
def with_db_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = sqlite3.connect('agents.db')
        try:
            result = func(conn, *args, **kwargs)
            conn.commit()
            return result
        finally:
            conn.close()
    return wrapper

# Initialize database with proper schema
@with_db_connection
def init_agent_db(conn):
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            agent_id TEXT PRIMARY KEY NOT NULL,
            name TEXT NOT NULL,
            background_info TEXT NOT NULL,
            personality_traits TEXT NOT NULL,
            knowledge_base_links TEXT NOT NULL,
            communication_style TEXT NOT NULL
        )
    ''')
    
    # 插入测试数据
    test_agents = [
        {
            "agent_id": "A001",
            "name": "Dr. Smith",
            "background_info": {"education": "PhD in AI", "skills": ["reasoning", "coding"]},
            "personality_traits": {"mood": "optimistic", "thinking": "logical", "mbti": "INTJ"},
            "knowledge_base_links": ["http://example.com/ai-knowledge"],
            "communication_style": {"style": "formal", "tone": "clear"}
        },
        {
            "agent_id": "A002",
            "name": "Prof. Jones",
            "background_info": {"education": "Masters in Economics", "skills": ["analysis", "finance"]},
            "personality_traits": {"mood": "serious", "thinking": "analytical", "mbti": "ENTJ"},
            "knowledge_base_links": ["http://example.com/econ-knowledge"],
            "communication_style": {"style": "formal", "tone": "precise"}
        },
        {
            "agent_id": "A003",
            "name": "Ms. Lee",
            "background_info": {"education": "BSc in Psychology", "skills": ["empathy", "communication"]},
            "personality_traits": {"mood": "cheerful", "thinking": "creative", "mbti": "ENFP"},
            "knowledge_base_links": ["http://example.com/psych-knowledge"],
            "communication_style": {"style": "friendly", "tone": "warm"}
        }
    ]
    
    for agent_data in test_agents:
        cursor.execute('''
            INSERT OR IGNORE INTO agents 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            agent_data["agent_id"],
            agent_data["name"],
            json.dumps(agent_data["background_info"]),
            json.dumps(agent_data["personality_traits"]),
            json.dumps(agent_data["knowledge_base_links"]),
            json.dumps(agent_data["communication_style"])
        ))
    
    print("Agent database initialized with test data")

# Define the Agent class to represent an AI agent
class Agent:
    def __init__(self, agent_id, name, background_info, personality_traits, knowledge_base_links, communication_style):
        self.agent_id = agent_id
        self.name = name
        self.background_info = background_info
        self.personality_traits = personality_traits  # Now includes "mbti" field
        self.knowledge_base_links = knowledge_base_links
        self.communication_style = communication_style

# Function to add an agent to the database
@with_db_connection
def create_agent(conn, agent_data):
    cursor = conn.cursor()

    # Check if the agent already exists
    if get_agent(agent_data["agent_id"]):
        print(f"Agent with ID {agent_data['agent_id']} already exists!")
        return

    agent = Agent(
        agent_data["agent_id"],
        agent_data["name"],
        agent_data["background_info"],
        agent_data["personality_traits"],
        agent_data["knowledge_base_links"],
        agent_data["communication_style"]
    )

    cursor.execute('''
        INSERT INTO agents (agent_id, name, background_info, personality_traits, knowledge_base_links, communication_style)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        agent.agent_id,
        agent.name,
        json.dumps(agent.background_info),
        json.dumps(agent.personality_traits),
        json.dumps(agent.knowledge_base_links),
        json.dumps(agent.communication_style)
    ))

    print(f"Agent {agent.name} added successfully!")

# Function to retrieve an agent from the database by ID 
@with_db_connection
def get_agent(conn, agent_id):
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM agents WHERE agent_id = ?', (agent_id,))
    row = cursor.fetchone()

    if row:
        agent = Agent(
            row[0],  # agent_id
            row[1],  # name
            json.loads(row[2]),  # background_info
            json.loads(row[3]),  # personality_traits
            json.loads(row[4]),  # knowledge_base_links
            json.loads(row[5])   # communication_style
        )
        return agent
    return None

# Improved Function to list all agents with better filters 
@with_db_connection
def list_agents(conn, filters=None):
    cursor = conn.cursor()

    query = 'SELECT * FROM agents'
    if filters:
        conditions = []
        if "skills" in filters:
            skill = filters["skills"]
            conditions.append(f"background_info LIKE '%{skill}%'")
        if "mbti" in filters:
            mbti = filters["mbti"]
            conditions.append(f"personality_traits LIKE '%{mbti}%'")
        if "mood" in filters:
            mood = filters["mood"]
            conditions.append(f"personality_traits LIKE '%{mood}%'")
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query)
    rows = cursor.fetchall()

    agents = []
    for row in rows:
        agent = Agent(
            row[0],  # agent_id
            row[1],  # name
            json.loads(row[2]),  # background_info
            json.loads(row[3]),  # personality_traits
            json.loads(row[4]),  # knowledge_base_links
            json.loads(row[5])   # communication_style
        )
        agents.append(agent)
    return agents

# Function to update an existing agent's data
@with_db_connection
def update_agent(conn, agent_id, agent_data):
    cursor = conn.cursor()

    if not get_agent(agent_id):
        print(f"No agent found with ID {agent_id}!")
        return False

    cursor.execute('''
        UPDATE agents SET
            name = ?,
            background_info = ?,
            personality_traits = ?,
            knowledge_base_links = ?,
            communication_style = ?
        WHERE agent_id = ?
    ''', (
        agent_data["name"],
        json.dumps(agent_data["background_info"]),
        json.dumps(agent_data["personality_traits"]),
        json.dumps(agent_data["knowledge_base_links"]),
        json.dumps(agent_data["communication_style"]),
        agent_id
    ))

    print(f"Agent {agent_id} updated successfully!")
    return True

# Function to delete an agent from the database
@with_db_connection
def delete_agent(conn, agent_id):
    if not get_agent(agent_id):
        print(f"No agent found with ID {agent_id}!")
        return False

    cursor = conn.cursor()
    cursor.execute('DELETE FROM agents WHERE agent_id = ?', (agent_id,))
    print(f"Agent {agent_id} deleted successfully!")
    return True

# Improved Function to get a random set of agents with diversity
@with_db_connection
def get_random_agents(conn, num_agents, diversity_parameters=None):
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agents')
    rows = cursor.fetchall()

    agents = [Agent(
        row[0],  # agent_id
        row[1],  # name
        json.loads(row[2]),  # background_info
        json.loads(row[3]),  # personality_traits
        json.loads(row[4]),  # knowledge_base_links
        json.loads(row[5])   # communication_style
    ) for row in rows]

    if len(agents) < num_agents:
        print(f"Only {len(agents)} agents available, returning all.")
        # 只返回agent_id列表，而不是Agent对象
        return [agent.agent_id for agent in agents]

    if diversity_parameters and "mbti" in diversity_parameters:
        # Ensure diverse MBTI types
        mbti_types = set()
        diverse_agents = []
        shuffled_agents = random.sample(agents, len(agents))  # Shuffle the list
        for agent in shuffled_agents:
            mbti = agent.personality_traits.get("mbti", "Unknown")
            if mbti not in mbti_types:
                diverse_agents.append(agent)
                mbti_types.add(mbti)
            if len(diverse_agents) >= num_agents:
                break
        return [agent.agent_id for agent in diverse_agents[:num_agents]]
    else:
        return random.sample([agent.agent_id for agent in agents], num_agents)

# Test the code with multiple agents and new features
if __name__ == "__main__":
    # Agent 1: Dr. Smith (INTJ)
    agent1_data = {
        "agent_id": "A002",
        "name": "Dr. Smith",
        "background_info": {"education": "PhD in AI", "skills": ["reasoning", "coding"]},
        "personality_traits": {"mood": "optimistic", "thinking": "logical", "mbti": "INTJ"},
        "knowledge_base_links": ["http://example.com/ai-knowledge"],
        "communication_style": {"style": "formal", "tone": "clear"}
    }

    # Agent 2: Prof. Jones (ENTJ)
    agent2_data = {
        "agent_id": "A003",
        "name": "Prof. Jones",
        "background_info": {"education": "Masters in Economics", "skills": ["analysis", "finance"]},
        "personality_traits": {"mood": "serious", "thinking": "analytical", "mbti": "ENTJ"},
        "knowledge_base_links": ["http://example.com/econ-knowledge"],
        "communication_style": {"style": "formal", "tone": "precise"}
    }

    # Agent 3: Ms. Lee (ENFP)
    agent3_data = {
        "agent_id": "A004",
        "name": "Ms. Lee",
        "background_info": {"education": "BSc in Psychology", "skills": ["empathy", "communication"]},
        "personality_traits": {"mood": "cheerful", "thinking": "creative", "mbti": "ENFP"},
        "knowledge_base_links": ["http://example.com/psych-knowledge"],
        "communication_style": {"style": "friendly", "tone": "warm"}
    }

    # Agent 4: Mr. Patel (ISTP)
    agent4_data = {
        "agent_id": "A005",
        "name": "Mr. Patel",
        "background_info": {"education": "BS in Engineering", "skills": ["problem-solving", "mechanics"]},
        "personality_traits": {"mood": "calm", "thinking": "practical", "mbti": "ISTP"},
        "knowledge_base_links": ["http://example.com/eng-knowledge"],
        "communication_style": {"style": "casual", "tone": "direct"}
    }

    # Create all agents
    create_agent(agent1_data)
    create_agent(agent2_data)
    create_agent(agent3_data)
    create_agent(agent4_data)

    # Retrieve and display one agent (handle missing MBTI)
    agent = get_agent("A003")
    if agent:
        mbti = agent.personality_traits.get("mbti", "Unknown")  # Use .get() to avoid KeyError
        print(f"Retrieved Agent: {agent.name}, MBTI: {mbti}")

    # List all agents
    all_agents = list_agents()
    print(f"All Agents: {[agent.name + ' (' + agent.personality_traits.get('mbti', 'Unknown') + ')' for agent in all_agents]}")

    # Test filters
    print("Filter Tests:")
    filtered_by_skill = list_agents({"skills": "reasoning"})
    print(f"Agents with 'reasoning' skill: {[agent.name for agent in filtered_by_skill]}")
    
    filtered_by_mbti = list_agents({"mbti": "INTJ"})
    print(f"Agents with 'INTJ' MBTI: {[agent.name for agent in filtered_by_mbti]}")
    
    filtered_by_mood = list_agents({"mood": "cheerful"})
    print(f"Agents with 'cheerful' mood: {[agent.name for agent in filtered_by_mood]}")
    
    filtered_combined = list_agents({"skills": "analysis", "mbti": "ENTJ"})
    print(f"Agents with 'analysis' skill and 'ENTJ' MBTI: {[agent.name for agent in filtered_combined]}")

    # Get 2 random agents with MBTI diversity
    random_diverse_agents = get_random_agents(2, {"mbti": True})
    print(f"Random Diverse Agents (by MBTI): {[agent for agent in random_diverse_agents]}")

    # Get 3 random agents without diversity
    random_agents = get_random_agents(3)
    print(f"Random Agents: {[agent for agent in random_agents]}")

    # Update an agent
    updated_data = {
        "agent_id": "A002",
        "name": "Dr. Smith Updated",
        "background_info": {"education": "PhD in AI", "skills": ["reasoning", "teaching"]},
        "personality_traits": {"mood": "cheerful", "thinking": "logical", "mbti": "INTJ"},
        "knowledge_base_links": ["http://example.com/ai-knowledge", "http://example.com/teaching"],
        "communication_style": {"style": "friendly", "tone": "clear"}
    }
    update_agent("A002", updated_data)

    # List agents again to see the update
    all_agents = list_agents()
    print(f"Updated Agents: {[agent.name + ' (' + agent.personality_traits.get('mbti', 'Unknown') + ')' for agent in all_agents]}")

    # Delete an agent
    delete_agent("A005")

    # List agents to confirm deletion
    all_agents = list_agents()
    print(f"Remaining Agents: {[agent.name + ' (' + agent.personality_traits.get('mbti', 'Unknown') + ')' for agent in all_agents]}")
