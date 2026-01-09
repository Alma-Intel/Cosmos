from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from .events_db import (
    get_sales_stage_metrics,
    get_followups_detection
)

def get_metrics_for_agent(agent_uuid, start_date=None):
    """Get an agent performance metrics on database."""
    if not agent_uuid:
        return []

    try:
        db_name = "analytics"
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
        
        table_name = getattr(settings, 'ANALYTICS_TABLE_NAME', 'analytics')
        agent_id_col = getattr(settings, 'ANALYTICS_AGENT_ID_COLUMN', 'agent_uuid')
        timestamp_col = getattr(settings, 'ANALYTICS_TIMESTAMP_COLUMN', 'created_at')
        
        params = [str(agent_uuid)]

        query = f"""
            SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, {timestamp_col}, agent_uuid
            FROM {table_name}
            WHERE {agent_id_col} = %s
            ORDER BY {timestamp_col} ASC
        """

        if start_date:
            query = f"""
                SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, {timestamp_col}, agent_uuid
                FROM {table_name}
                WHERE {agent_id_col} = %s
                AND {timestamp_col} >= %s
                ORDER BY {timestamp_col} ASC
            """
            params.append(start_date)
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, tuple(params))
        
        metrics = cursor.fetchall()
        
        metrics_list = [dict(row) for row in metrics]
        
        cursor.close()
        conn.close()
        
        return metrics_list
        
    except Exception as e:
        print(f"Unexpected error fetching metrics: {e}")
        return []

def get_metrics_for_team_members(team_members_uuids, start_date=None):
    """ Get all team members performance metrics on database."""
    if not team_members_uuids:
        return []

    try:
        db_name = "analytics"
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
        
        table_name = getattr(settings, 'ANALYTICS_TABLE_NAME', 'analytics')
        agent_id_col = getattr(settings, 'ANALYTICS_AGENT_ID_COLUMN', 'agent_uuid')
        timestamp_col = getattr(settings, 'ANALYTICS_TIMESTAMP_COLUMN', 'created_at')
        
        params = [tuple(str(uid) for uid in team_members_uuids)]

        query = f"""
            SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, {timestamp_col}, agent_uuid
            FROM {table_name}
            WHERE {agent_id_col} IN %s
            ORDER BY {timestamp_col} ASC
        """

        if start_date:
            query = f"""
                SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, {timestamp_col}, agent_uuid
                FROM {table_name}
                WHERE {agent_id_col} IN %s
                AND {timestamp_col} >= %s
                ORDER BY {timestamp_col} ASC
            """
            params.append(start_date)
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, tuple(params))
        
        metrics = cursor.fetchall()
        
        metrics_list = [dict(row) for row in metrics]
        
        cursor.close()
        conn.close()
        
        return metrics_list
        
    except Exception as e:
        print(f"Unexpected error fetching metrics: {e}")
        return []


def get_objections_from_database(team_members_uuids, start_date=None):
    """Get objections detected for a team from the analytics database."""
    objections_detected = []
    try:
        if not team_members_uuids:
            return objections_detected
        
        db_name = "analytics"
        analytics_db = settings.DATABASES.get(db_name)
        if not analytics_db:
            if settings.DEBUG:
                print("Analytics database not configured")
            return objections_detected
        
        uuids_formatted = tuple(str(uid) for uid in team_members_uuids)
        params = [uuids_formatted]

        query = """
            SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, created_at, agent_uuid
            FROM analytics
            WHERE agent_uuid IN %s
            AND analysis_type = 'SALES_PERFORMANCE'
            ORDER BY created_at ASC
        """

        if start_date:
            query = """
                SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, created_at, agent_uuid
                FROM analytics
                WHERE agent_uuid IN %s
                AND analysis_type = 'SALES_PERFORMANCE'
                AND created_at >= %s
                ORDER BY created_at ASC
            """
            params.append(start_date)

        with psycopg2.connect(
            host=analytics_db.get('HOST', 'localhost'),
            port=analytics_db.get('PORT', '5432'),
            database=analytics_db.get('NAME', 'events_db'),
            user=analytics_db.get('USER', 'postgres'),
            password=analytics_db.get('PASSWORD', '')
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, tuple(params))
                results = cursor.fetchall()
                objections_detected = [dict(event) for event in results]
        
        if settings.DEBUG:
            print(f"Fetched {len(objections_detected)} objections from database.")

        return objections_detected
        
    except psycopg2.Error as e:
        if settings.DEBUG:
            print(f"Error fetching objections from PostgreSQL: {e}")
        return objections_detected
    
    except Exception as e:
        if settings.DEBUG:
            print(f"Unexpected error fetching objections: {e}")
        return objections_detected
    
def format_objection_data(objections_list, team_members_dict):
    """Format objections data to get frequency and resolution scores by objection type."""
    if not objections_list:
        return []

    stats = defaultdict(lambda: {
        'count': 0, 
        'total_score': 0, 
        'sellers': defaultdict(list), 
        'responses': []
    })

    for obj in objections_list:
        result = obj.get('result', {})
        objections_results = result.get('objection_details', {}).get('objections_detected', [])

        seller_id = obj.get('agent_uuid') or obj.get('seller_uuid') or 'Desconhecido'
        lookup_key = str(seller_id).strip().lower() if seller_id else 'Desconhecido'
        seller_name = seller_id
        if lookup_key in team_members_dict:
            seller_name = team_members_dict[lookup_key]
        for item in objections_results:

            obj_type = item.get('objection_type', 'other')
            score = item.get('resolution_quality', 0)
            response_text = item.get('seller_response', '')

            stats[obj_type]['count'] += 1
            stats[obj_type]['total_score'] += score
            stats[obj_type]['sellers'][seller_name].append(score)
            
            stats[obj_type]['responses'].append({
                'seller': seller_name,
                'score': score,
                'text': response_text
            })

    formatted_data = []
    
    type_map = {
        'price': 'Preço', 
        'trust': 'Confiança', 
        'timing': 'Tempo', 
        'competitor': 'Concorrente', 
        'product_fit': 'Adequação', 
        'other': 'Outro',
        'hesitation': 'Hesitação',
        'payment_method': 'Método de Pagamento',
        'implicit_price': 'Preço Implícito',
        'implicit_timing': 'Tempo Implícito'
    }

    for otype, data in stats.items():
        avg_score = data['total_score'] / data['count']
        
        seller_averages = {
            seller: sum(scores)/len(scores) 
            for seller, scores in data['sellers'].items()
        }
        
        if not seller_averages:
            continue

        best_seller = max(seller_averages, key=seller_averages.get)
        worst_seller = min(seller_averages, key=seller_averages.get)
        
        best_seller_responses = [r for r in data['responses'] if r['seller'] == best_seller]
        
        if best_seller_responses:

            best_response_obj = max(best_seller_responses, key=lambda x: x['score'])
            best_response_text = best_response_obj['text']
        else:
            best_response_text = max(data['responses'], key=lambda x: x['score'])['text']

        formatted_data.append({
            'type': type_map.get(otype, otype.capitalize()),
            'freq': data['count'],
            'score': int(avg_score),
            'best': best_seller,
            'worst': worst_seller,
            'best_response': best_response_text
        })

    return sorted(formatted_data, key=lambda x: x['freq'], reverse=True)

def format_critical_objections(raw_objections, team_members_dict, infobip_conversations_url=None):
    """Format objections data to get critical objections across the team."""
    critical_objections_list = []
    type_map = {
        'price': 'Preço', 
        'trust': 'Confiança', 
        'timing': 'Tempo', 
        'competitor': 'Concorrente', 
        'product_fit': 'Adequação', 
        'other': 'Outro',
        'hesitation': 'Hesitação',
        'payment_method': 'Método de Pagamento',
        'implicit_price': 'Preço Implícito',
        'implicit_timing': 'Tempo Implícito'
    }

    try:
        for row in raw_objections:
            result = row.get('result', {})
            details = result.get('objection_details', {}).get('objections_detected', [])
            raw_uuid = row.get('agent_uuid')

            if raw_uuid:
                lookup_key = str(raw_uuid).strip().lower()
                agent_name = team_members_dict.get(lookup_key, lookup_key)

            else:
                agent_name = 'Sem Nome'

            created_at = row.get('created_at')

            conversation_uuid = row.get('conversation_uuid')

            for item in details:
                score = item.get('resolution_quality', 0)
                
                if score < 60 and score != 0:
                    obj_type = item.get('objection_type', 'other')
                    
                    critical_objections_list.append({
                        'agent': agent_name,
                        'type': type_map.get(obj_type, obj_type.capitalize()),
                        'score': score,
                        'text': item.get('objection_text', ''),
                        'response': item.get('seller_response', ''),
                        'time': created_at,
                        'conversation_uuid': row.get('conversation_uuid'),
                        'url': f"{infobip_conversations_url}{conversation_uuid}" if conversation_uuid else "#"
                    })
        
        critical_objections_list.sort(key=lambda x: (x['score'], x['time']), reverse=False)
        return critical_objections_list
    
    except Exception as e:
        if settings.DEBUG:
            print(f"Error processing critical objections: {e}")
        return []

def format_objection_resolution_for_team(raw_objections, team_members_dict, infobip_conversations_url=None):
    """Format objections data to get best and worst resolved objections per seller."""
    type_map = {
        'price': 'Preço', 
        'trust': 'Confiança', 
        'timing': 'Tempo', 
        'competitor': 'Concorrente', 
        'product_fit': 'Adequação', 
        'other': 'Outro',
        'hesitation': 'Hesitação',
        'payment_method': 'Método de Pagamento',
        'implicit_price': 'Preço Implícito',
        'implicit_timing': 'Tempo Implícito'
    }

    seller_groups = defaultdict(list)
    detailed_objections = []

    try:
        for row in raw_objections:
            result = row.get('result', {})
            details = result.get('objection_details', {}).get('objections_detected', [])
            
            raw_uuid = row.get('agent_uuid')
            lookup_key = str(raw_uuid).strip().lower() if raw_uuid else None
            agent_name = team_members_dict.get(lookup_key, lookup_key) if lookup_key else 'Sem Nome'
            conv_uuid = row.get('conversation_uuid', '')

            for item in details:
                obj_type = item.get('objection_type', 'other')
                score = item.get('resolution_quality', 0)
                response = item.get('seller_response', '-')


                if (response is None or 
                    (isinstance(response, str) and not response.strip()) or
                    response.lower() in ['null', 'none']):
                    response = 'Sem Resposta'
                else:
                    response = f'"{response}"'
                
                obj_data = {
                    'seller': agent_name,
                    'type': type_map.get(obj_type, obj_type.capitalize()),
                    'score': score,
                    'objection_text': item.get('objection_text', '-'),
                    'response_text': response,
                    'conversation_id': conv_uuid,
                    'url': f"{infobip_conversations_url}{conv_uuid}" if conv_uuid else "#",
                    'created_at': row.get('created_at')
                }
                seller_groups[agent_name].append(obj_data)
    except Exception as e:
        if settings.DEBUG:
            print(f"Error processing objections for sellers: {e}")
        return []

    try:
        for seller, items in seller_groups.items():
            if not items:
                continue
                
            best_item = max(items, key=lambda x: x['score'])
            worst_item = min(items, key=lambda x: x['score'])

            if best_item == worst_item:
                detailed_objections.append(best_item)
            else:
                detailed_objections.append(best_item)
                detailed_objections.append(worst_item)

        detailed_objections.sort(key=lambda x: x['seller'])
        return detailed_objections
    
    except Exception as e:
        if settings.DEBUG:
            print(f"Error compiling detailed objections: {e}")
        return []
    
def format_objection_resolution_by_seller(raw_objections, user_profile, infobip_conversations_url=None):
    """Format objections data to get best and worst resolved objections for an agent by objection type."""
    type_map = {
        'price': 'Preço', 
        'trust': 'Confiança', 
        'timing': 'Tempo', 
        'competitor': 'Concorrente', 
        'product_fit': 'Adequação', 
        'other': 'Outro',
        'hesitation': 'Hesitação',
        'payment_method': 'Método de Pagamento',
        'implicit_price': 'Preço Implícito',
        'implicit_timing': 'Tempo Implícito'
    }

    type_groups = defaultdict(list)
    detailed_objections = []

    try:
        agent_name = user_profile.get_display_name()

        for row in raw_objections:
            result = row.get('result', {})
            details = result.get('objection_details', {}).get('objections_detected', [])
            conv_uuid = row.get('conversation_uuid', '')

            for item in details:
                obj_type = item.get('objection_type', 'other')
                score = item.get('resolution_quality', 0)
                if score == 0:
                    continue
                
                response = item.get('seller_response', '-')

                if (response is None or 
                    (isinstance(response, str) and not response.strip()) or
                    response.lower() in ['null', 'none']):
                    response = 'Sem Resposta'
                
                obj_data = {
                    'seller': agent_name,
                    'type': type_map.get(obj_type, obj_type.capitalize()),
                    'raw_type': obj_type,
                    'score': score,
                    'objection_text': item.get('objection_text', '-'),
                    'response_text': response,
                    'conversation_id': conv_uuid,
                    'url': f"{infobip_conversations_url}{conv_uuid}" if conv_uuid else "#",
                    'created_at': row.get('created_at')
                }
                
                type_groups[obj_type].append(obj_data)

    except Exception as e:
        if settings.DEBUG: print(f"Error parsing objections: {e}")
        return []

    try:
        sorted_types = sorted(type_groups.items(), key=lambda item: len(item[1]), reverse=True)
        top_5_types = sorted_types[:5]

        for obj_type, items in top_5_types:
            if not items: continue

            best_item = max(items, key=lambda x: x['score'])
            best_item['tag'] = 'Melhor Prática'
            best_item['row_style'] = 'best'

            worst_item = min(items, key=lambda x: x['score'])
            worst_item['tag'] = 'Ponto de Atenção'
            worst_item['row_style'] = 'worst'

            detailed_objections.append(best_item)
            
            if best_item != worst_item:
                detailed_objections.append(worst_item)

        detailed_objections.sort(key=lambda x: x['type'])
        
        return detailed_objections

    except Exception as e:
        if settings.DEBUG: print(f"Error compiling top 5 objections: {e}")
        return []

def calculate_agent_scores(agent, analysis_list, start_date=None):
    """Calculate various performance scores for a given agent."""
    if not agent or not agent.external_uuid:
        return {}
    
    agent_uuid = str(agent.external_uuid).strip()
    if not agent_uuid:
        return {}
    
    seller_data = {
        'seller_name': agent.user.username,
        'real_name': agent.user.first_name,
        'uuid': agent_uuid
    }

    sales_data = get_sales_stage_metrics([agent_uuid], start_date=start_date)
    
    seller_data['total_conversations'] = sales_data.get('total_conversations', 0)
    seller_data['sale_stage_distribution'] = sales_data.get('raw_stages', {})
    seller_data['total_sales'] = sales_data.get('total_sales', 0)

    followups = get_followups_detection([agent_uuid], start_date=start_date)
    total_followups = sum(f.get('count', 0) for f in followups)

    seller_data['total_followups'] = total_followups

    if seller_data['total_conversations'] > 0:
        seller_data['follow_up_rate'] = (total_followups / seller_data['total_conversations']) * 100
    else:
        seller_data['follow_up_rate'] = 0


    scores = [a.get('result', {}).get('score') for a in analysis_list if a.get('analysis_type') == 'SENTIMENT_ANALYSIS']
    scores = [s for s in scores if s is not None]
    
    seller_data['avg_performance'] = (sum(scores) / len(scores)) if scores else 0

    best_practices_list = get_best_practices(analysis_list)
    
    counts = {
        'discount_score_sum': 0,
        'attempted_meetings': 0,
        'meetings_accepted': 0,
        'meetings_scheduled': 0,
        'referrals_attempted': 0,
        'referrals_received': 0
    }

    bp_count = len(best_practices_list)

    for item in best_practices_list:
        # Discount
        d_score = item.get('discount_strategies', {}).get('discount_execution_score')
        counts['discount_score_sum'] += d_score if d_score else 0

        # Meetings
        mp = item.get('meeting_planning', {})
        if mp.get('attempted_meeting_scheduling') in [True, 'true']:
            counts['attempted_meetings'] += 1
        if mp.get('meeting_accepted') in [True, 'true']:
            counts['meetings_accepted'] += 1
        if mp.get('scheduled_datetime') not in [None, 'null']:
            counts['meetings_scheduled'] += 1
            
        # Referrals
        ref = item.get('referral_requests', {})
        if ref.get('attempted_referral_request') in [True, 'true']:
            counts['referrals_attempted'] += 1
        counts['referrals_received'] += ref.get('referrals_received_count', 0)


    base_count = bp_count if bp_count > 0 else 1

    seller_data['discount_strategy_rate'] = (counts['discount_score_sum'] / base_count)
    seller_data['meeting_attempt_rate'] = (counts['attempted_meetings'] / base_count) * 100
    seller_data['meeting_success_rate'] = (counts['meetings_accepted'] / base_count) * 100
    seller_data['referral_request_rate'] = (counts['referrals_attempted'] / base_count) * 100
    
    seller_data['meetings_scheduled'] = counts['meetings_scheduled']
    seller_data['referrals_received'] = counts['referrals_received']

    sales_performance_list = get_sales_performance(analysis_list)
    obj_resolved = 0
    obj_total = 0
    
    for item in sales_performance_list:
        objs = item.get('objection_details', {}).get('objections_detected', [])
        for obj in objs:
            obj_total += 1
            if obj.get('resolved') in [True, 'true']:
                obj_resolved += 1
                
    seller_data['objection_resolution_rate'] = (obj_resolved / obj_total * 100) if obj_total > 0 else 0
    
    seller_data['avg_seller_messages'] = 0 
    seller_data['referral_conversion_rate'] = 0

    return seller_data
    

def get_team_summary_stats(team_members, start_date=None):
    """Calculate aggregate statistics for a team based on its members' data."""
    from .analytics_metrics import get_metrics_for_agent, calculate_agent_scores

    aggregates = {
        'total_conversations': 0,
        'total_sales': 0,
        'total_followups': 0,
        'total_meetings': 0,
        'sum_performance': 0,
        'active_agents': 0
    }

    for member in team_members:
        analysis_list = get_metrics_for_agent(member.external_uuid, start_date)
        agent_data = calculate_agent_scores(member, analysis_list, start_date=start_date)
        
        if not agent_data: continue

        aggregates['total_conversations'] += agent_data.get('total_conversations', 0)
        aggregates['total_sales'] += agent_data.get('total_sales', 0)
        aggregates['total_followups'] += agent_data.get('total_followups', 0)
        aggregates['total_meetings'] += agent_data.get('meetings_scheduled', 0)
        
        avg_perf = agent_data.get('avg_performance', 0)
        if avg_perf > 0:
            aggregates['sum_performance'] += avg_perf
            aggregates['active_agents'] += 1

    num_agents = aggregates['active_agents'] if aggregates['active_agents'] > 0 else 1
    
    conversion_rate = 0
    if aggregates['total_conversations'] > 0:
        conversion_rate = (aggregates['total_sales'] / aggregates['total_conversations']) * 100

    return {
        'total_conversations': aggregates['total_conversations'],
        'total_sales': aggregates['total_sales'],
        'conversion_rate': round(conversion_rate, 2),
        'total_followups': aggregates['total_followups'],
        'total_meetings': aggregates['total_meetings'],
        'avg_performance': round(aggregates['sum_performance'] / num_agents, 2)
    }

def get_stage_scores(analysis_list, members_analysis=None):
    """Maps sales stage keys to Portuguese labels and compiles agent and team average scores."""
    LABEL_TRANSLATIONS = {
        'closing': 'Fechamento',
        'connection': 'Conexão',
        'explanation': 'Explicação',
        'objection_handling': 'Contorno de Objeções'
    }

    labels = []
    agent_data = []
    raw_keys_order = []

    for analysis in analysis_list:
        analysis_type = analysis.get('analysis_type', '')
        results = analysis.get('result', {})
        
        if analysis_type == "STAGE_SCORE":
            for key, value in results.items():
                raw_keys_order.append(key)
                
                translated_label = LABEL_TRANSLATIONS.get(key, key.replace('_', ' ').title())
                labels.append(translated_label)
                
                agent_data.append(value)
            break

    team_avg_data = []

    if members_analysis and raw_keys_order:
        team_scores_accumulator = defaultdict(list)

        for member_record in members_analysis:
            if member_record.get('analysis_type') == "STAGE_SCORE":
                member_result = member_record.get('result', {})
                
                for k, v in member_result.items():
                    if isinstance(v, (int, float)):
                        team_scores_accumulator[k].append(v)

        for key in raw_keys_order:
            scores_list = team_scores_accumulator.get(key, [])
            if scores_list:
                avg = sum(scores_list) / len(scores_list)
                team_avg_data.append(round(avg, 1))
            else:
                team_avg_data.append(0)
    
    if not team_avg_data:
        team_avg_data = [0] * len(agent_data)

    metrics_data = {
        'labels': labels,
        'agent_data': agent_data,
        'team_avg': team_avg_data 
    }
    
    return metrics_data

def get_sales_performance(analysis_list):
    """Get sales performance data from analysis list."""
    stages_perfomance = []

    for analysis in analysis_list:
        analysis_type = analysis.get('analysis_type', '')
        results = analysis.get('result', {})
        if analysis_type == "SALES_PERFORMANCE":
            stages_performance_dict = {}
            if results:
                objection_detected = results.get('objections_detected', [])
                performance_scores = results.get('performance_scores', {})
                overall_performance_assessment = results.get('overall_performance_assessment', {})
                
                stages_performance_dict['objections_detected'] = objection_detected
                stages_performance_dict['performance_scores'] = performance_scores
                stages_performance_dict['overall_performance_assessment'] = overall_performance_assessment
                
                stages_perfomance.append(stages_performance_dict)

    return stages_perfomance

def get_best_practices(analysis_list):
    """Get sales best practices data from analysis list."""
    best_practices_list = []

    for analysis in analysis_list:
        best_practices = {}
        analysis_type = analysis.get('analysis_type', '')
        results = analysis.get('result', {})
        if analysis_type == "BEST_PRACTICES":
            if results:
                best_practices['meeting_planning'] = results.get('meeting_planning', {})
                best_practices['referral_requests'] = results.get('referral_requests', {})
                best_practices['discount_strategies'] = results.get('discount_strategies', {})
                best_practices['payment_communication'] = results.get('payment_communication', {})
                best_practices_list.append(best_practices)

    return best_practices_list

def get_sentiment_analysis(analysis_list):
    """Get the sentiment analysis data from analysis list."""
    sentiment_analysis_list = []

    for analysis in analysis_list:
        sentiment_analysis = {}
        analysis_type = analysis.get('analysis_type', '')
        results = analysis.get('result', {})
        if analysis_type == "SENTIMENT_ANALYSIS":
            if results:
                sentiment_analysis['score'] = results.get('score', 0)
                sentiment_analysis_list.append(sentiment_analysis)

    return sentiment_analysis_list

def get_team_aggregates(team_members, start_date=None):
    """
    Calculate team aggregates and individual seller analytics.
    Args:
        - team_members: List of team member objects with 'external_uuid' and 'user' attributes.
        - start_date: Optional start date for filtering metrics.

    Returns:
        - team_aggregates: Dictionary with aggregated team metrics.
        - sellers_analytics: List of dictionaries with individual seller analytics.
        - num_agents: Number of active agents with performance data.
    
    """
    team_aggregates = {
        'total_conversations': 0,
        'total_sales': 0,
        'meetings_scheduled': 0,
        'referrals_received': 0,
        'total_follow_ups': 0,
        'sum_performance': 0,
        'count_performance': 0,
        
        'sum_followup_rate': 0,
        'sum_meeting_attempt': 0,
        'sum_meeting_success': 0,
        'sum_referral_req': 0,
        'sum_discount_strat': 0,
        'sum_objection_res': 0,
        'active_agents_count': 0
    }

    sellers_analytics = []

    for member in team_members:
        analysis_list = get_metrics_for_agent(member.external_uuid, start_date=start_date)
        agent_data = calculate_agent_scores(member, analysis_list, start_date=start_date)
        
        if not agent_data: continue

        sellers_analytics.append(agent_data)

        team_aggregates['total_conversations'] += agent_data.get('total_conversations', 0)
        team_aggregates['total_sales'] += agent_data.get('total_sales', 0)
        team_aggregates['meetings_scheduled'] += agent_data.get('meetings_scheduled', 0)
        team_aggregates['referrals_received'] += agent_data.get('referrals_received', 0)
        team_aggregates['total_follow_ups'] += agent_data.get('total_followups', 0)
        
        team_aggregates['sum_performance'] += agent_data.get('avg_performance', 0)
        team_aggregates['count_performance'] += 1 if agent_data.get('avg_performance', 0) > 0 else 0

        team_aggregates['sum_followup_rate'] += agent_data.get('follow_up_rate', 0)
        team_aggregates['sum_meeting_attempt'] += agent_data.get('meeting_attempt_rate', 0)
        team_aggregates['sum_meeting_success'] += agent_data.get('meeting_success_rate', 0)
        team_aggregates['sum_referral_req'] += agent_data.get('referral_request_rate', 0)
        team_aggregates['sum_discount_strat'] += agent_data.get('discount_strategy_rate', 0)
        team_aggregates['sum_objection_res'] += agent_data.get('objection_resolution_rate', 0)
        
        team_aggregates['active_agents_count'] += 1

    num_agents = team_aggregates['active_agents_count'] if team_aggregates['active_agents_count'] > 0 else 1
    
    team_aggregates['team_conversion_rate'] = 0
    if team_aggregates['total_conversations'] > 0:
        team_aggregates['team_conversion_rate'] = (team_aggregates['total_sales'] / team_aggregates['total_conversations']) * 100

    return team_aggregates, sellers_analytics, num_agents

    
