### Supabase
from supabase import create_client, Client
from typing import List, Dict, Any, Optional
import os

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert(table: str, data: Dict[str, Any]) -> Dict:
    """
    Insert a new row into the table.
    :param table: Table name
    :param data: Dictionary of column:value pairs
    :return: Response dict
    """
    response = supabase.table(table).insert(data).execute()
    return response.data

def select(table: str, columns: List[str] = None, filters: Dict[str, Any] = None) -> List[Dict]:
    """
    Select rows from a table with optional filters and column selection.
    :param table: Table name
    :param columns: List of columns to select (default all)
    :param filters: Dictionary of column:value to filter
    :return: List of rows
    """
    query = supabase.table(table)
    
    if columns:
        query = query.select(','.join(columns))
    else:
        query = query.select('*')
    
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    
    response = query.execute()
    return response.data

def update(table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict:
    """
    Update rows in a table based on filters.
    :param table: Table name
    :param data: Dictionary of columns to update
    :param filters: Dictionary of column:value to filter
    :return: Response dict
    """
    query = supabase.table(table)
    for key, value in filters.items():
        query = query.eq(key, value)
    response = query.update(data).execute()
    return response.data

def upsert(table: str, data: List[Dict[str, Any]]) -> Dict:
    """
    Insert or update rows based on primary key conflict.
    :param table: Table name
    :param data: List of dictionaries
    :return: Response dict
    """
    response = supabase.table(table).upsert(data).execute()
    return response.data


def delete(table: str, filters: Dict[str, Any]) -> List[Dict]:
    """
    Delete rows in a table based on filters.
    :param table: Table name
    :param filters: Dictionary of column:value to filter
    :return: List of deleted rows
    """
    query = supabase.table(table)
    for key, value in filters.items():
        query = query.eq(key, value)
    response = query.delete().execute()
    return response.data