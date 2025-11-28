"""
Views for the conversations app
"""
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .mongodb import (
    get_conversations_collection,
    get_all_sellers,
    get_all_tags,
    get_all_sales_stages,
    get_uuid_to_email_mapping,
    map_seller_to_email
)


@login_required
def conversation_list(request):
    """List all conversations with filtering options"""
    try:
        collection = get_conversations_collection()
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(
            f"<h1>MongoDB Connection Error</h1>"
            f"<p>Unable to connect to MongoDB. Please check your MONGODB_URL environment variable.</p>"
            f"<p>Error: {str(e)}</p>"
            f"<p>Make sure MONGODB_URL, MONGODB_DB_NAME, and MONGODB_COLLECTION_NAME are set in Railway.</p>",
            status=500
        )
    
    # Get filter parameters from request
    seller_id = request.GET.get('seller_id', '')
    sales_stage = request.GET.get('sales_stage', '')
    tag = request.GET.get('tag', '')
    search = request.GET.get('search', '')
    
    # Build MongoDB query
    query = {}
    and_conditions = []
    
    if seller_id:
        query['envolvedSellers'] = seller_id
    
    if sales_stage:
        # Try exact match first, then regex for partial matches
        query['metadata.salesStage'] = {'$regex': sales_stage, '$options': 'i'}
    
    if tag:
        # Search for tag in clientTagsInput (could be string or array)
        tag_query = {
            '$or': [
                {'metadata.clientTagsInput': {'$regex': tag, '$options': 'i'}},
                {'metadata.clientTagsInput': tag}
            ]
        }
        and_conditions.append(tag_query)
    
    if search:
        # Search in client name, email, or chatId
        search_query = {
            '$or': [
                {'metadata.clientName': {'$regex': search, '$options': 'i'}},
                {'metadata.clientEmail': {'$regex': search, '$options': 'i'}},
                {'chatId': {'$regex': search, '$options': 'i'}}
            ]
        }
        and_conditions.append(search_query)
    
    # Combine all conditions
    if and_conditions:
        if query:
            and_conditions.append(query)
            query = {'$and': and_conditions}
        else:
            query = {'$and': and_conditions} if len(and_conditions) > 1 else and_conditions[0]
    
    # Get conversations
    # First, check total count for debugging
    total_count = collection.count_documents(query)
    
    # Get conversations from MongoDB
    conversations_cursor = collection.find(query).sort('lastUpdate', -1)
    conversations = list(conversations_cursor)
    
    # Get UUID to email mapping (once, use for all operations)
    uuid_to_email_map = get_uuid_to_email_mapping()
    
    if settings.DEBUG:
        print(f"UUID to email map loaded with {len(uuid_to_email_map)} entries")
        if uuid_to_email_map:
            sample_uuid = list(uuid_to_email_map.keys())[0]
            print(f"Sample entry: {sample_uuid} -> {uuid_to_email_map[sample_uuid]}")
    
    # Convert ObjectId to string for each conversation (for template access)
    # Also map seller UUIDs to emails
    for conv in conversations:
        conv['id'] = str(conv['_id'])  # Add 'id' field that templates can access
        
        # Map seller UUIDs to emails
        if 'envolvedSellers' in conv and conv['envolvedSellers']:
            conv['envolvedSellersDisplay'] = []
            for seller in conv['envolvedSellers']:
                mapped = map_seller_to_email(seller, uuid_to_email_map)
                conv['envolvedSellersDisplay'].append(mapped)
                if settings.DEBUG:
                    if seller in uuid_to_email_map:
                        print(f"Mapped {seller} -> {mapped}")
                    else:
                        print(f"No mapping for {seller}, using UUID")
        else:
            conv['envolvedSellersDisplay'] = []
    
    # Get filter options (with error handling)
    try:
        all_sellers_raw = get_all_sellers()
        # Map sellers to display names (email if available, otherwise UUID)
        all_sellers = [
            {
                'uuid': seller,
                'display': map_seller_to_email(seller, uuid_to_email_map)
            }
            for seller in all_sellers_raw
        ]
    except Exception as e:
        all_sellers = []
        if settings.DEBUG:
            print(f"Error getting sellers: {e}")
    
    try:
        all_tags = get_all_tags()
    except Exception as e:
        all_tags = []
        if settings.DEBUG:
            print(f"Error getting tags: {e}")
    
    try:
        all_sales_stages = get_all_sales_stages()
    except Exception as e:
        all_sales_stages = []
        if settings.DEBUG:
            print(f"Error getting sales stages: {e}")
    
    # Pagination - use a simple approach
    page_number = int(request.GET.get('page', 1))
    per_page = 20
    total_pages = (len(conversations) + per_page - 1) // per_page if conversations else 0
    
    # Calculate pagination slice
    start_idx = (page_number - 1) * per_page
    end_idx = start_idx + per_page
    paginated_conversations = conversations[start_idx:end_idx]
    
    # Debug info (only in DEBUG mode)
    debug_info = None
    if settings.DEBUG:
        debug_info = {
            'query': str(query),
            'total_count': total_count,
            'conversations_list_length': len(conversations),
            'paginated_length': len(paginated_conversations),
            'page_number': page_number,
            'start_idx': start_idx,
            'end_idx': end_idx,
            'collection_name': settings.MONGODB_COLLECTION_NAME,
            'db_name': settings.MONGODB_DB_NAME,
        }
    
    context = {
        'conversations': paginated_conversations,
        'all_conversations_count': len(conversations),
        'total_pages': total_pages,
        'current_page': page_number,
        'has_previous': page_number > 1,
        'has_next': page_number < total_pages,
        'previous_page': page_number - 1 if page_number > 1 else None,
        'next_page': page_number + 1 if page_number < total_pages else None,
        'all_sellers': all_sellers,
        'all_tags': all_tags,
        'all_sales_stages': all_sales_stages,
        'current_seller_id': seller_id,
        'current_sales_stage': sales_stage,
        'current_tag': tag,
        'current_search': search,
        'debug_info': debug_info,
    }
    
    return render(request, 'conversations/list.html', context)


@login_required
def conversation_detail(request, conversation_id):
    """View detailed information about a specific conversation"""
    try:
        collection = get_conversations_collection()
    except Exception as e:
        from django.http import HttpResponse
        return HttpResponse(
            f"<h1>MongoDB Connection Error</h1>"
            f"<p>Unable to connect to MongoDB. Please check your MONGODB_URL environment variable.</p>"
            f"<p>Error: {str(e)}</p>"
            f"<p>Make sure MONGODB_URL, MONGODB_DB_NAME, and MONGODB_COLLECTION_NAME are set in Railway.</p>",
            status=500
        )
    
    # Get conversation by _id (ObjectId) or chatId
    from bson import ObjectId
    from bson.errors import InvalidId
    conversation = None
    
    try:
        # Try to find by ObjectId first
        conversation = collection.find_one({'_id': ObjectId(conversation_id)})
    except (InvalidId, ValueError):
        # If that fails, try by chatId
        conversation = collection.find_one({'chatId': conversation_id})
    
    if not conversation:
        from django.http import Http404
        raise Http404("Conversation not found")
    
    # Sort messages by timestamp
    messages = conversation.get('mensagens', [])
    messages.sort(key=lambda x: x.get('messageTimestamp', ''))
    
    # Convert ObjectId to string for template (add 'id' field that templates can access)
    conversation['id'] = str(conversation['_id'])
    
    # Get UUID to email mapping and map seller UUIDs to emails
    uuid_to_email_map = get_uuid_to_email_mapping()
    envolved_sellers = conversation.get('envolvedSellers', [])
    envolved_sellers_display = []
    for seller in envolved_sellers:
        mapped = map_seller_to_email(seller, uuid_to_email_map)
        envolved_sellers_display.append(mapped)
        if settings.DEBUG and seller in uuid_to_email_map:
            print(f"Mapped {seller} -> {mapped}")
    
    # Normalize tags - convert string to list if needed
    metadata = conversation.get('metadata', {})
    tags = metadata.get('clientTagsInput')
    if tags and isinstance(tags, str):
        # If tags is a string, split by comma
        metadata['clientTagsInput'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
    elif not tags:
        metadata['clientTagsInput'] = []
    
    context = {
        'conversation': conversation,
        'messages': messages,
        'metadata': metadata,
        'envolved_sellers': envolved_sellers_display,
    }
    
    return render(request, 'conversations/detail.html', context)

