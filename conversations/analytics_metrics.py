from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from .events_db import (
    get_sales_stage_metrics,
    get_followups_detection
)

def get_metrics_for_agent(agent_uuid):
    """[WIP] Get an agent performance metrics on database."""
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
        
        query = f"""
            SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, {timestamp_col}, agent_uuid
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


def get_objections_from_database(team_members_uuids):
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
        
        query = """
            SELECT uuid, conversation_uuid, analysis_type, result, alma_internal_organization, created_at agent_uuid
            FROM analytics
            WHERE agent_uuid IN %s
            AND analysis_type = 'SALES_PERFORMANCE'
            ORDER BY created_at ASC
        """

        with psycopg2.connect(
            host=analytics_db.get('HOST', 'localhost'),
            port=analytics_db.get('PORT', '5432'),
            database=analytics_db.get('NAME', 'events_db'),
            user=analytics_db.get('USER', 'postgres'),
            password=analytics_db.get('PASSWORD', '')
        ) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (uuids_formatted,))
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
    if not objections_list:
        return []

    stats = defaultdict(lambda: {
        'count': 0, 
        'total_score': 0, 
        'sellers': defaultdict(list), 
        'responses': []
    })

    objections_results_list = []

    for obj in objections_list:
        result = obj.get('result', {})
        objections_results = result.get('objection_details', {}).get('objections_detected', [])

        for item in objections_results:
            item['agent_uuid'] = obj.get('agent_uuid')

        objections_results_list.extend(objections_results)

    for obj in objections_results_list:
        obj_type = obj.get('objection_type', 'other')
        score = obj.get('resolution_quality', 0)
        response_text = obj.get('seller_response', '')
        
        seller_id = obj.get('agent_uuid') or obj.get('seller_uuid') or 'Desconhecido'
        seller_name = seller_id
        
        if seller_id in team_members_dict:
            seller_name = team_members_dict[seller_id]

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
        'hesitation': 'Hesitação'
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

def calculate_agent_scores(agent, analysis_list):
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

    sales_data = get_sales_stage_metrics([agent_uuid])
    
    seller_data['total_conversations'] = sales_data.get('total_conversations', 0)
    seller_data['sale_stage_distribution'] = sales_data.get('raw_stages', {})
    seller_data['total_sales'] = sales_data.get('total_sales', 0)

    followups = get_followups_detection([agent_uuid])
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
    

def get_team_summary_stats(team_members):
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
        analysis_list = get_metrics_for_agent(member.external_uuid)
        agent_data = calculate_agent_scores(member, analysis_list)
        
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

def get_stage_scores(analysis_list):
    LABEL_TRANSLATIONS = {
        'closing': 'Fechamento',
        'connection': 'Conexão',
        'explanation': 'Explicação',
        'objection_handling': 'Contorno de Objeções'
    }

    labels = []
    agent_data = []

    for analysis in analysis_list:
        analysis_type = analysis.get('analysis_type', '')
        results = analysis.get('result', {})
        
        if analysis_type == "STAGE_SCORE":
            for key, value in results.items():
                translated_label = LABEL_TRANSLATIONS.get(key, key.replace('_', ' ').title())
                
                labels.append(translated_label)
                agent_data.append(value)
            break

    team_avg_temp = [50 for _ in labels]

    metrics_data = {
        'labels': labels,
        'agent_data': agent_data,
        'team_avg': team_avg_temp,
    }
    
    return metrics_data

def get_sales_performance(analysis_list):
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


def get_metrics_for_agent_mock(agent_uuid):
    metrics_data = {
        'labels': ['Vendas', 'Conversão', 'Tempo Resp.', 'NPS', 'Retenção', 'Volume'],
        'agent_data': [85, 70, 90, 88, 60, 75],
        'team_avg': [70, 65, 70, 80, 70, 70],
    }

    return metrics_data