"""
Functions to interact with the events PostgreSQL database
"""
from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2.extras import RealDictCursor


def get_events_for_conversation(conversation_id):
    """
    Fetch all events for a given conversation from the events database.
    Returns events sorted by timestamp (most recent first).
    
    Args:
        conversation_id: The conversation ID (chatId) to fetch events for
        
    Returns:
        List of event dictionaries, sorted by timestamp (most recent first)
    """
    try:
        # Get the events database connection
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return []
        
        # Connect to the events database
        conn = psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        )
        
        table_name = getattr(settings, 'EVENTS_TABLE_NAME', 'events')
        conversation_id_col = getattr(settings, 'EVENTS_CONVERSATION_ID_COLUMN', 'conversation_infobip_uuid')
        timestamp_col = getattr(settings, 'EVENTS_TIMESTAMP_COLUMN', 'datetime')
        
        # Query events for this conversation, ordered by timestamp (most recent first)
        # Use parameterized query to prevent SQL injection
        # Select specific columns: event_type, datetime, and origin (dialogue or agent_infobip_uuid)
        query = f"""
            SELECT id, event_type, {timestamp_col} as datetime, dialogue, agent_infobip_uuid, event_subtype, json
            FROM {table_name}
            WHERE {conversation_id_col} = %s
            ORDER BY {timestamp_col} DESC
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (conversation_id,))
        
        events = cursor.fetchall()
        
        # Convert RealDictRow objects to regular dictionaries
        events_list = [dict(event) for event in events]
        
        cursor.close()
        conn.close()
        
        if settings.DEBUG:
            print(f"Fetched {len(events_list)} events for conversation {conversation_id}")
        
        return events_list
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching events from PostgreSQL: {e}")
        return []
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching events: {e}")
        return []


def get_sales_stage_change_events(team_members_uuids):
    mock_funnel = {
        'Contato Inicial': 150,
        'Apresentação': 85,
        'Proposta Enviada': 42,
        'Aguardando Pagamento': 20,
        'Comprou': 12,
        'Lead Perdido': 35
    }

    try:
        if not team_members_uuids:
            return mock_funnel
            
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return mock_funnel
        
        conn = psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        )
        
        uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
        
        query = """
            SELECT json->>'NEW_STAGE' as stage, COUNT(*) as count
            FROM events
            WHERE event_type = 'SALES_STAGE_CHANGE'
            AND agent_uuid IN %s
            GROUP BY json->>'NEW_STAGE'
            ORDER BY count DESC
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (uuids_formatted,))
        
        results = cursor.fetchall()
        events_dict = {row[0]: row[1] for row in results if row[0]}
        
        cursor.close()
        conn.close()
        
        if settings.DEBUG:
            print(f"Fetched {len(events_dict)} stages for conversation team.")
        
        if len(events_dict) == 0:
            return mock_funnel

        return events_dict
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching events from PostgreSQL: {e}")
        return mock_funnel
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching events: {e}")
        return mock_funnel

def get_objections_events_for_team(team_members_uuids):
    try:
        if not team_members_uuids:
            return {}
            
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return {}
        
        conn = psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        )
        
        uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
        
        query = """
            SELECT json->>'OBJECTION_TYPE' as objection_type, COUNT(*) as count
            FROM events
            WHERE event_type = 'OBJECTION_DETECTION'
            AND agent_uuid IN %s
            GROUP BY json->>'OBJECTION_DETECTION'
            ORDER BY count DESC
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (uuids_formatted,))
        
        results = cursor.fetchall()
        events_dict = {row[0]: row[1] for row in results if row[0]}
        
        cursor.close()
        conn.close()
        
        if settings.DEBUG:
            print(f"Fetched {len(events_dict)} objection events.")
        
        return events_dict
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching events from PostgreSQL: {e}")
        return {}
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching events: {e}")
        return {}