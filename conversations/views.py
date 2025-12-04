"""
Views for the conversations app
"""
import uuid
import json
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime
from .models import Conversation, Message
from .events_db import get_events_for_conversation


def is_user_admin(user):
    """Check if user is an admin"""
    try:
        profile = user.profile
        return profile.is_admin()
    except:
        return False


def get_user_organization(user):
    """Get the user's alma_internal_organization from their profile and convert to UUID"""
    try:
        profile = user.profile
        org_str = profile.alma_internal_organization
        if not org_str:
            return None
        # Convert string to UUID for database comparison
        try:
            return uuid.UUID(str(org_str))
        except (ValueError, AttributeError):
            return None
    except:
        return None


def conversation_to_dict(conv):
    """Convert Conversation model instance to dictionary for template compatibility"""
    # Ensure agents is a list
    agents = conv.agents or []
    if isinstance(agents, str):
        # If agents is a string, try to parse it
        try:
            agents = json.loads(agents)
            if not isinstance(agents, list):
                agents = []
        except:
            agents = []
    
    return {
        'id': str(conv.id),
        'chatId': str(conv.id),  # Use UUID as chatId for now
        'uuid': str(conv.id),
        'lastUpdate': conv.updated_at,
        'metadata': conv.metadata or {},
        'envolvedSellers': agents,
        'envolvedSellersDisplay': agents,
        'agents': agents,
        'external_participants': conv.external_participants or [],
        'mensagens': [],  # Will be populated separately
        'created_at': conv.created_at,
        'updated_at': conv.updated_at,
        'origin': conv.origin,
    }


def message_to_dict(msg):
    """Convert Message model instance to dictionary for template compatibility"""
    # Handle datetime - make timezone-aware if needed
    created_at = msg.created_at
    if created_at and created_at.tzinfo is None:
        # If naive datetime, assume it's in UTC
        created_at = timezone.make_aware(created_at, timezone.utc)
    
    message_timestamp_parsed = None
    if created_at:
        try:
            message_timestamp_parsed = timezone.localtime(created_at)
        except (ValueError, AttributeError):
            # Fallback to the original datetime if localtime fails
            message_timestamp_parsed = created_at
    
    return {
        'id': str(msg.id),
        'sender_uuid': str(msg.sender_uuid),
        'conversation_uuid': str(msg.conversation_uuid),
        'content': msg.content,
        'type': msg.type,
        'link': msg.link,
        'channel': msg.channel,
        'subchannel': msg.subchannel,
        'messageTimestamp': msg.created_at,
        'messageTimestamp_parsed': message_timestamp_parsed,
        'created_at': msg.created_at,
        'updated_at': msg.updated_at,
        'metadata': msg.metadata or {},
        'origin': msg.origin,
    }


@login_required
def conversation_list(request):
    """List all conversations with filtering options"""
    # Check if user is admin
    is_admin = is_user_admin(request.user)
    
    # Get user's organization for filtering (only if not admin)
    user_org = None
    if not is_admin:
        user_org = get_user_organization(request.user)
        
        if not user_org:
            from django.http import HttpResponse
            return HttpResponse(
                f"<h1>Access Error</h1>"
                f"<p>Your user profile does not have an alma_internal_organization set.</p>"
                f"<p>Please contact an administrator.</p>",
                status=403
            )
    
    # Get filter parameters from request
    seller_id = request.GET.get('seller_id', '')
    sales_stage = request.GET.get('sales_stage', '')
    tag = request.GET.get('tag', '')
    search = request.GET.get('search', '')
    
    # Start with base queryset - filter by organization only if not admin
    if is_admin:
        queryset = Conversation.objects.all()
    else:
        queryset = Conversation.objects.filter(alma_internal_organization=user_org)
    
    # Apply filters
    if seller_id:
        # Filter conversations where agents list contains seller_id
        queryset = queryset.filter(agents__contains=[seller_id])
    
    if sales_stage:
        # Filter by sales stage in metadata JSON field
        queryset = queryset.filter(metadata__salesStage__icontains=sales_stage)
    
    if tag:
        # Filter by tag in metadata JSON field (could be string or array)
        queryset = queryset.filter(
            Q(metadata__clientTagsInput__icontains=tag) |
            Q(metadata__clientTagsInput__contains=tag)
        )
    
    if search:
        # Search in metadata fields (clientName, clientEmail) or UUID
        queryset = queryset.filter(
            Q(metadata__clientName__icontains=search) |
            Q(metadata__clientEmail__icontains=search) |
            Q(id__icontains=search)
        )
    
    # Order by updated_at descending
    queryset = queryset.order_by('-updated_at')
    
    # Get filter options from the filtered queryset
    all_agents_set = set()
    all_tags_set = set()
    all_sales_stages_set = set()
    
    # Sample conversations to get filter options (limit for performance)
    sample_convs = queryset[:1000]
    for conv in sample_convs:
        # Collect agents - properly handle the array
        agents = conv.agents
        if agents:
            # ArrayField should return a list, but handle edge cases
            if isinstance(agents, list):
                # Normal case: it's a list
                for agent in agents:
                    if agent and str(agent).strip():  # Only add non-empty agents
                        all_agents_set.add(str(agent).strip())
            elif isinstance(agents, (tuple, set)):
                # Handle other iterable types
                for agent in agents:
                    if agent and str(agent).strip():
                        all_agents_set.add(str(agent).strip())
            elif isinstance(agents, str):
                # If it's a string, it might be a PostgreSQL array text representation
                # Try to parse it or handle as comma-separated
                if agents.startswith('{') and agents.endswith('}'):
                    # PostgreSQL array format: {item1,item2}
                    agents_str = agents[1:-1]  # Remove curly braces
                    agent_list = [a.strip().strip('"').strip("'") for a in agents_str.split(',') if a.strip()]
                    for agent in agent_list:
                        if agent:
                            all_agents_set.add(agent)
                else:
                    # Try JSON parsing
                    try:
                        parsed = json.loads(agents)
                        if isinstance(parsed, list):
                            for agent in parsed:
                                if agent:
                                    all_agents_set.add(str(agent).strip())
                    except:
                        # Last resort: treat as single value if not empty
                        if agents.strip():
                            all_agents_set.add(agents.strip())
        
        # Collect tags from metadata
        metadata = conv.metadata or {}
        tags = metadata.get('clientTagsInput')
        if tags:
            if isinstance(tags, str):
                tag_list = [t.strip() for t in tags.split(',') if t.strip()]
                all_tags_set.update(tag_list)
            elif isinstance(tags, list):
                all_tags_set.update([str(t) for t in tags if t])
        
        # Collect sales stages
        sales_stage = metadata.get('salesStage')
        if sales_stage:
            all_sales_stages_set.add(str(sales_stage))
    
    all_sellers = [{'uuid': agent, 'display': agent} for agent in sorted(all_agents_set)]
    all_tags = sorted(all_tags_set)
    all_sales_stages = sorted(all_sales_stages_set)
    
    # Pagination using Django's Paginator
    page_number = int(request.GET.get('page', 1))
    per_page = 20
    paginator = Paginator(queryset, per_page)
    
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)
        page_number = 1
    
    # Convert model instances to dictionaries for template compatibility
    conversations = []
    for conv in page_obj:
        conv_dict = conversation_to_dict(conv)
        # Get message count for this conversation - skip org filter for admins
        message_query = Message.objects.filter(conversation_uuid=conv.id)
        if not is_admin:
            message_query = message_query.filter(alma_internal_organization=user_org)
        message_count = message_query.count()
        conv_dict['mensagens'] = [None] * message_count  # Placeholder for count
        conversations.append(conv_dict)
    
    # Debug info (only in DEBUG mode)
    debug_info = None
    if settings.DEBUG:
        debug_info = {
            'total_count': queryset.count(),
            'conversations_list_length': len(conversations),
            'paginated_length': len(conversations),
            'page_number': page_number,
            'total_pages': paginator.num_pages,
            'user_organization': user_org,
        }
    
    context = {
        'conversations': conversations,
        'all_conversations_count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_number,
        'has_previous': page_obj.has_previous(),
        'has_next': page_obj.has_next(),
        'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
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
    # Check if user is admin
    is_admin = is_user_admin(request.user)
    
    # Get user's organization for filtering (only if not admin)
    user_org = None
    if not is_admin:
        user_org = get_user_organization(request.user)
        
        if not user_org:
            raise Http404("Your user profile does not have an alma_internal_organization set.")
    
    try:
        # Try to get conversation by UUID - skip org filter for admins
        conversation_uuid = conversation_id
        if is_admin:
            conversation = Conversation.objects.get(id=conversation_uuid)
        else:
            conversation = Conversation.objects.get(
                id=conversation_uuid,
                alma_internal_organization=user_org
            )
    except (Conversation.DoesNotExist, ValueError):
        raise Http404("Conversation not found or you don't have access to it")
    
    # Get messages for this conversation - skip org filter for admins
    messages_qs = Message.objects.filter(conversation_uuid=conversation.id)
    if not is_admin:
        messages_qs = messages_qs.filter(alma_internal_organization=user_org)
    messages_qs = messages_qs.order_by('created_at')
    
    # Convert messages to dictionaries
    messages = [message_to_dict(msg) for msg in messages_qs]
    
    # Convert conversation to dictionary
    conv_dict = conversation_to_dict(conversation)
    conv_dict['lastUpdate'] = conversation.updated_at
    
    # Get metadata
    metadata = conversation.metadata or {}
    
    # Normalize tags - ensure it's a list
    tags = metadata.get('clientTagsInput')
    if tags and isinstance(tags, str):
        metadata['clientTagsInput'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
    elif not tags:
        metadata['clientTagsInput'] = []
    
    # Get agents/sellers for display - ensure it's a list
    agents = conversation.agents or []
    if isinstance(agents, str):
        try:
            agents = json.loads(agents)
            if not isinstance(agents, list):
                agents = []
        except:
            agents = []
    envolved_sellers_display = agents
    
    # Fetch events for this conversation from the events database
    chat_id = str(conversation.id)
    events = get_events_for_conversation(chat_id)
    
    # Parse event timestamps to datetime objects for display
    for event in events:
        timestamp_col = getattr(settings, 'EVENTS_TIMESTAMP_COLUMN', 'datetime')
        datetime_value = event.get('datetime') or event.get(timestamp_col)
        
        if datetime_value:
            try:
                dt = None
                if isinstance(datetime_value, str):
                    # Try parsing ISO format
                    try:
                        dt = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
                    except ValueError:
                        try:
                            dt = datetime.strptime(datetime_value, '%Y-%m-%dT%H:%M:%S.%f%z')
                        except ValueError:
                            try:
                                dt = datetime.strptime(datetime_value, '%Y-%m-%dT%H:%M:%S%z')
                            except ValueError:
                                # Try PostgreSQL timestamp format
                                try:
                                    dt = datetime.strptime(datetime_value, '%Y-%m-%d %H:%M:%S.%f%z')
                                except ValueError:
                                    try:
                                        dt = datetime.strptime(datetime_value, '%Y-%m-%d %H:%M:%S%z')
                                    except ValueError:
                                        dt = None
                elif isinstance(datetime_value, datetime):
                    dt = datetime_value
                
                if dt:
                    if dt.tzinfo is None:
                        dt = timezone.make_aware(dt, timezone.utc)
                    event['datetime_parsed'] = timezone.localtime(dt)
            except Exception as e:
                if settings.DEBUG:
                    print(f"Error parsing event timestamp: {e}")
    
    context = {
        'conversation': conv_dict,
        'messages': messages,
        'metadata': metadata,
        'envolved_sellers': envolved_sellers_display,
        'events': events,
    }
    
    return render(request, 'conversations/detail.html', context)
