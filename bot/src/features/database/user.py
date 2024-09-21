from features.database import get_connection
from util import tuple_to_dict

def add_user(user_id: int):
    conn = get_connection()

    query = 'INSERT INTO users(id) VALUES (%s)'

    cursor = conn.cursor()
    cursor.execute(query, (user_id,))

    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id: int):
    conn = get_connection()

    query = 'SELECT id, derivation_path, slippage, chain_id, token0_address, token0_name, token1_address, token1_name FROM users WHERE id=%s'

    cursor = conn.cursor()
    cursor.execute(query, (user_id,))

    user = cursor.fetchone()
    if not user:
        return None
    
    return tuple_to_dict(user, ['id', 'derivation_path', 'slippage', 'chain_id', 'token0_address', 'token0_name', 'token1_address', 'token1_name'])
    
