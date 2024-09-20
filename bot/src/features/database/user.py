from features.database import get_connection
from util import tuple_to_dict

def add_user(user_id: int):
    conn = get_connection()

    # TODO: Get proper derivation path. Query all existing derivation paths and increment from the latest one.
    # Alternate idea: Instead of storing the full derivation path, we can store a single integer in AUTO_INCREMENT mode,
    # then we form the derivation key from that.
    derivation_path = "m/0'/0"

    query = 'INSERT INTO users(id, derivation_path) VALUES (%s, %s)'

    cursor = conn.cursor()
    cursor.execute(query, (user_id, derivation_path))

    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id: int):
    conn = get_connection()

    query = 'SELECT id, derivation_path, chain_id FROM users WHERE id=%s'

    cursor = conn.cursor()
    cursor.execute(query, (user_id,))

    if cursor.rowcount == 0:
        return None

    user = cursor.fetchone()

    return tuple_to_dict(user, ['id', 'derivation_path', 'chain_id'])
