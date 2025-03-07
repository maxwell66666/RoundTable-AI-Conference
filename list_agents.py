import sqlite3
import json

def print_agents():
    conn = sqlite3.connect('C:\\WORK\\code\\RoundTable\\agents.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM agents')
    rows = cursor.fetchall()
    
    print("系统中的专家列表:")
    print("-" * 80)
    
    for row in rows:
        agent_id = row[0]
        name = row[1]
        background_info = json.loads(row[2])
        personality_traits = json.loads(row[3])
        knowledge_base_links = json.loads(row[4])
        communication_style = json.loads(row[5])
        
        print(f"专家ID: {agent_id}")
        print(f"姓名: {name}")
        print("背景信息:")
        for key, value in background_info.items():
            print(f"  - {key}: {value}")
        print("人格特质:")
        for key, value in personality_traits.items():
            print(f"  - {key}: {value}")
        print("沟通风格:")
        for key, value in communication_style.items():
            print(f"  - {key}: {value}")
        print("-" * 80)
    
    conn.close()

if __name__ == "__main__":
    print_agents() 