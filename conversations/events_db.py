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


def get_sales_stage_metrics(team_members_uuids):
    LABEL_TRANSLATIONS = {
        'purchased_payment_confirmed': 'Pagamento Confirmado', 
        'active_client_support_request': 'Suporte de Cliente Ativo', 
        'explaining_solution_product': 'Explicando Produto', 
        'introduction_conversation_started': 'Introdução', 
        'lost_lead_no_engagement': 'Lead Sem Engajamento', 
        'proposal_sent_awaiting_decision': 'Proposta Enviada', 
        'awaiting_payment_terms_agreed': 'Aguardando Pagamento'
    }
    
    mock_data = {
        'stages': {'Introdução': 100, 'Pagamento Confirmado': 10},
        'total_conversations': 100,
        'total_sales': 10,
        'conversion_rate': 10.0
    }

    try:
        if not team_members_uuids:
            return mock_data
            
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return {}

        query_stages = """
            SELECT json->>'NEW_STAGE' as stage, COUNT(*) as count
            FROM events
            WHERE event_type = 'SALES_STAGE_CHANGE'
            AND agent_uuid IN %s
            GROUP BY json->>'NEW_STAGE'
        """

        query_total = """
            SELECT COUNT(DISTINCT conversation_uuid)
            FROM events
            WHERE event_type = 'SALES_STAGE_CHANGE'
            AND agent_uuid IN %s
        """

        with psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
                cursor.execute(query_stages, (uuids_formatted,))
                stage_results = cursor.fetchall()

                cursor.execute(query_total, (uuids_formatted,))
                total_conversations_count = cursor.fetchone()['count']

        
        translated_stages = {}
        raw_stages = {}
        sales_count = 0

        for row in stage_results:
            raw_stage = row.get('stage')
            count = row['count']
            
            if not raw_stage: continue
            label = LABEL_TRANSLATIONS.get(raw_stage, raw_stage.replace('_', ' ').title())
            translated_stages[label] = count
            raw_stages[raw_stage] = count

            if raw_stage == 'purchased_payment_confirmed':
                sales_count = count
        
        if not translated_stages:
            return mock_data

        conversion_rate = 0
        if total_conversations_count > 0:
            conversion_rate = (sales_count / total_conversations_count) * 100

        return {
            'stages': translated_stages,
            'raw_stages': raw_stages,
            'total_conversations': total_conversations_count,
            'total_sales': sales_count,
            'conversion_rate': round(conversion_rate, 2)
        }

    except Exception as e:
        if settings.DEBUG: print(f"Unexpected error fetching stages: {e}")
        return mock_data
    
def get_followups_detection(team_members_uuids):
    followups_detected = []
    try:
        if not team_members_uuids:
            return followups_detected
            
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return followups_detected
        
        uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
        
        query = """
            SELECT json->>'FOLLOWUP_TRY' as followup_try, COUNT(*) as count
            FROM events
            WHERE event_type = 'FOLLOWUP_DETECTION'
            AND agent_uuid IN %s
            GROUP BY json->>'FOLLOWUP_TRY'
            ORDER BY count DESC
        """

        with psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (uuids_formatted,))
                results = cursor.fetchall()
                followups_detected = [dict(event) for event in results]
        
        if settings.DEBUG:
            print(f"Fetched {len(followups_detected)} followups for conversation team.")

        return followups_detected
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching followups from PostgreSQL: {e}")
        return followups_detected
    
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching followups: {e}")
        return followups_detected

def get_objections_events_for_team(team_members_uuids):
    try:
        if not team_members_uuids:
            return []
            
        events_db = settings.DATABASES.get('events')
        if not events_db:
            if settings.DEBUG:
                print("Events database not configured")
            return []
        
        uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
        
        query = """
            SELECT json->>'OBJECTION_TYPE' as objection_type, COUNT(*) as count
            FROM events
            WHERE event_type = 'OBJECTION_DETECTION'
            AND agent_uuid IN %s
            GROUP BY json->>'OBJECTION_DETECTION'
            ORDER BY count DESC
        """
        
        with psycopg2.connect(
            host=events_db.get('HOST', 'localhost'),
            port=events_db.get('PORT', '5432'),
            database=events_db.get('NAME', 'events_db'),
            user=events_db.get('USER', 'postgres'),
            password=events_db.get('PASSWORD', '')
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (uuids_formatted,))
                results = cursor.fetchall()
                events_list = [dict(event) for event in results]

        if settings.DEBUG:
            print(f"Fetched {len(events_list)} objection events.")
        
        return events_list
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching events from PostgreSQL: {e}")
        return []
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching events: {e}")
        return []