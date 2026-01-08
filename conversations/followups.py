"""
Functions to interact with the events PostgreSQL database
"""
import random
import string
from django.conf import settings
from django.db import connections
from django.utils import timezone
import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor


def get_followups_for_agent(agent_uuid):
    """Get all available followups for an agent on 'followups' database."""
    if not agent_uuid:
        return []

    try:
        db_config = settings.DATABASES.get('followups')
        if not db_config:
            print("Error: Database 'followups' not configured.")
            return []
        
        conn = psycopg2.connect(
            host=db_config.get('HOST', 'localhost'),
            port=db_config.get('PORT', '5432'),
            database=db_config.get('NAME'),
            user=db_config.get('USER'),
            password=db_config.get('PASSWORD')
        )
        
        table_name = getattr(settings, 'FOLLOWUPS_TABLE_NAME', 'follow_up')
        agent_id_col = getattr(settings, 'FOLLOWUPS_AGENT_ID_COLUMN', 'agent_uuid')
        timestamp_col = getattr(settings, 'FOLLOWUPS_TIMESTAMP_COLUMN', 'follow_up_date')
        
        query = f"""
            SELECT event_uuid, conversation_uuid, agent_uuid, score, {timestamp_col} as follow_up_date
            FROM {table_name}
            WHERE {agent_id_col} = %s
            ORDER BY {timestamp_col} ASC
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, (str(agent_uuid),))
        
        followups = cursor.fetchall()
        
        followup_list = [dict(row) for row in followups]
        
        cursor.close()
        conn.close()
        
        return followup_list
        
    except Exception as e:
        print(f"Unexpected error fetching follow-ups: {e}")
        return []
    

def get_link_tracking_for_agent(agent_uuid):
    """Get links created for an agent on 'link_tracking' table."""
    if not agent_uuid:
        return []

    try:
        db_config = settings.DATABASES.get('followups')
        if not db_config:
            print("Error: Database 'followups' not configured.")
            return []
        
        conn = psycopg2.connect(
            host=db_config.get('HOST', 'localhost'),
            port=db_config.get('PORT', '5432'),
            database=db_config.get('NAME'),
            user=db_config.get('USER'),
            password=db_config.get('PASSWORD')
        )
        
        query = """
            SELECT slug, original_url, seller_id
            FROM link_tracking
            WHERE seller_id = %s
        """
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, (agent_uuid,))
        
        links = cursor.fetchall()
        
        links_list = [dict(row) for row in links]
        
        cursor.close()
        conn.close()
        
        return links_list
        
    except Exception as e:
        print(f"[LINK TRACKING] Unexpected error fetching follow-ups: {e}")
        return []

def get_conversation_id(url, id_name, separator):
    """Get a conversation ID from a link."""
    try:
        return url.split(id_name)[1].split(separator)[0]
    
    except IndexError as e:
        print(f"Could not get id: {e}")
        return None

def create_tracked_link(original_url, seller_name):
    """Generate an unique slug, save on db and return a short link."""
    try:
        db_config = settings.DATABASES.get('followups')
        if not db_config:
            print("Error: Database 'followups' not configured.")
            return None
        
        conn = psycopg2.connect(
            host=db_config.get('HOST', 'localhost'),
            port=db_config.get('PORT', '5432'),
            database=db_config.get('NAME'),
            user=db_config.get('USER'),
            password=db_config.get('PASSWORD')
        )

    except Exception as e:
        print(f"Error trying to connect to database: {e}")
        return None

    base_url = "https://followupsbot-prod.up.railway.app"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT slug FROM link_tracking 
                WHERE original_url = %s AND seller_id = %s
            """, (original_url, seller_name))
            
            existing = cur.fetchone()
            
            if existing:
                slug = existing['slug'] if isinstance(existing, dict) else existing[0]
                conn.close()
                return f"{base_url}/r/{slug}"

    except Exception as e:
        print(f"Error trying to verify existing link: {e}")
        if conn: conn.close()
        return None

    chars = string.ascii_letters + string.digits

    for _ in range(5): 
        slug = ''.join(random.choice(chars) for _ in range(6))
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO link_tracking (slug, original_url, seller_id)
                    VALUES (%s, %s, %s)
                """, (slug, original_url, seller_name))
                
                conn.commit()
                conn.close()
                return f"{base_url}/r/{slug}"
                
        except errors.UniqueViolation:
            conn.rollback()
            continue
            
        except Exception as e:
            conn.rollback()
            print(f"Error trying to create new short link: {e}")
            if conn: conn.close()
            return original_url

    if conn: conn.close()
    return original_url

def create_infobip_conversation_link(conversationId):
    """Create a link for Infobip given a conversationId."""
    url = f"https://portal-ny2.infobip.com/conversations/my-work?conversationId={conversationId}"
    return url
    
def get_followups_priority(all_followups_list, followups_dict, high_priority_limit):
    """Ordinate follow-ups into high and low priority lists."""

    high_priority_tasks = []
    low_priority_tasks = []

    now = timezone.now()
    end = (now + timezone.timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)

    for task in all_followups_list:
        raw_uuid = task.get('conversation_uuid')

        if raw_uuid:
            conversation_id_key = str(raw_uuid).strip().lower().replace('-', '')
            task['original_url'] = followups_dict.get(conversation_id_key)
        else:
            task['original_url'] = None

        if not task['original_url']:
            task['original_url'] = create_infobip_conversation_link(str(raw_uuid or ''))

        task_date = task['follow_up_date']

        if timezone.is_naive(task_date):
            task_date = timezone.make_aware(task_date)
            task['follow_up_date'] = task_date

        if task_date <= now and task['score'] >= 700:
            if len(high_priority_tasks) < high_priority_limit:
                high_priority_tasks.append(task)
            else:
                low_priority_tasks.append(task)

        else:
            low_priority_tasks.append(task)

    print(f"High priority tasks: {len(high_priority_tasks)}, Low priority tasks: {len(low_priority_tasks)}")

    return high_priority_tasks, low_priority_tasks