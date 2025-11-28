"""
Views for the conversations app
"""
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .mongodb import (
    get_conversations_collection,
    get_all_sellers,
    get_all_tags,
    get_all_sales_stages
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
    conversations = list(collection.find(query).sort('lastUpdate', -1))
    
    # Convert ObjectId to string for each conversation (for template access)
    for conv in conversations:
        conv['id'] = str(conv['_id'])  # Add 'id' field that templates can access
    
    # Get filter options
    all_sellers = get_all_sellers()
    all_tags = get_all_tags()
    all_sales_stages = get_all_sales_stages()
    
    # Pagination
    paginator = Paginator(conversations, 20)  # Show 20 conversations per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'conversations': page_obj,
        'all_sellers': all_sellers,
        'all_tags': all_tags,
        'all_sales_stages': all_sales_stages,
        'current_seller_id': seller_id,
        'current_sales_stage': sales_stage,
        'current_tag': tag,
        'current_search': search,
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
    
    # Convert ObjectId to string for template
    conversation['_id'] = str(conversation['_id'])
    
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
        'envolved_sellers': conversation.get('envolvedSellers', []),
    }
    
    return render(request, 'conversations/detail.html', context)

