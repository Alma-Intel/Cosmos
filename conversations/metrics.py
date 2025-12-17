from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2.extras import RealDictCursor

def get_metrics_for_agent_db(agent_uuid):
    """[WIP] Get an agent performance metrics on database."""
    if not agent_uuid:
        return []

    try:
        db_name = "metrics"
        db_config = settings.DATABASES.get(db_name)
        
        if not db_config:
            print(f"Error: Database {db_name} not configured.")
            return []
        
        conn = psycopg2.connect(
            host=db_config.get('HOST', 'localhost'),
            port=db_config.get('PORT', '5432'),
            database=db_config.get('NAME'),
            user=db_config.get('USER'),
            password=db_config.get('PASSWORD')
        )
        
        table_name = getattr(settings, 'METRICS_TABLE_NAME', 'metrics')
        agent_id_col = getattr(settings, 'METRICS_AGENT_ID_COLUMN', 'agent_uuid')
        timestamp_col = getattr(settings, 'METRICS_TIMESTAMP_COLUMN', 'datetime')
        
        query = f"""
            SELECT agent_uuid, score, {timestamp_col}
            FROM {table_name}
            WHERE {agent_id_col} = %s
            ORDER BY {timestamp_col} ASC
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (str(agent_uuid),))
        
        metrics = cursor.fetchall()
        
        metrics_list = [dict(row) for row in metrics]
        
        cursor.close()
        conn.close()
        
        return metrics_list
        
    except Exception as e:
        print(f"Unexpected error fetching metrics: {e}")
        return []

def get_agent_team_metrics(agent_uuid):
    """[WIP] Get average metrics of agents from given agent's team."""
    pass

def get_metrics_for_agent(agent_uuid):
    metrics_data = {
        'labels': ['Vendas', 'Conversão', 'Tempo Resp.', 'NPS', 'Retenção', 'Volume'],
        'agent_data': [85, 70, 90, 88, 60, 75],
        'team_avg': [70, 65, 70, 80, 70, 70],
    }

    return metrics_data