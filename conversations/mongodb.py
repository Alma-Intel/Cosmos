"""
MongoDB connection and utility functions
"""
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
from django.conf import settings

# Cache for UUID to email mapping (loaded once at startup)
_UUID_TO_EMAIL_CACHE = None

# Cache for filter options (loaded once, refreshed on demand)
_ALL_SELLERS_CACHE = None
_ALL_TAGS_CACHE = None
_ALL_SALES_STAGES_CACHE = None


def get_mongodb_client():
    """Get MongoDB client connection"""
    mongodb_url = settings.MONGODB_URL
    
    # Check if MongoDB URL is configured (not using default localhost)
    if mongodb_url == 'mongodb://localhost:27017/':
        raise ConfigurationError(
            "MongoDB URL not configured. Please set MONGO_URL (or MONGODB_URL) environment variable in Railway."
        )
    
    try:
        # Connect with timeout settings
        client = MongoClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000
        )
        # Test the connection
        client.admin.command('ping')
        return client
    except ServerSelectionTimeoutError as e:
        raise ConnectionError(
            f"Could not connect to MongoDB at {mongodb_url}. "
            f"Please check your MONGO_URL environment variable. Error: {str(e)}"
        )
    except Exception as e:
        raise ConnectionError(
            f"MongoDB connection error: {str(e)}. "
            f"Please verify MONGO_URL (or MONGODB_URL), MONGODB_DB_NAME, and MONGODB_COLLECTION_NAME are set correctly."
        )


def get_conversations_collection():
    """Get the conversations collection from MongoDB"""
    client = get_mongodb_client()
    db = client[settings.MONGODB_DB_NAME]
    return db[settings.MONGODB_COLLECTION_NAME]


def get_all_sellers():
    """Get all unique seller IDs from conversations (cached, optimized)"""
    global _ALL_SELLERS_CACHE
    
    if _ALL_SELLERS_CACHE is not None:
        return _ALL_SELLERS_CACHE
    
    try:
        collection = get_conversations_collection()
        # Check if collection is empty
        if collection.count_documents({}) == 0:
            _ALL_SELLERS_CACHE = []
            return []
        
        # Use a more efficient approach: sample documents and extract sellers
        # This is much faster than processing all documents
        all_sellers = set()
        
        # Sample up to 5000 documents to get a representative set of sellers
        sample_size = min(5000, collection.count_documents({}))
        if sample_size > 0:
            pipeline = [
                {'$sample': {'size': sample_size}},
                {'$project': {'envolvedSellers': 1}},
                {'$match': {'envolvedSellers': {'$exists': True, '$ne': []}}},
                {'$unwind': '$envolvedSellers'},
                {'$group': {'_id': '$envolvedSellers'}},
                {'$project': {'_id': 0, 'seller': '$_id'}}
            ]
            
            try:
                sellers = list(collection.aggregate(pipeline, allowDiskUse=True, maxTimeMS=10000))
                all_sellers.update([item['seller'] for item in sellers if item.get('seller')])
            except Exception as agg_error:
                if settings.DEBUG:
                    print(f"Aggregation failed, trying fallback: {agg_error}")
                # Fallback: get distinct from a limited set
                for doc in collection.find({'envolvedSellers': {'$exists': True, '$ne': []}}, {'envolvedSellers': 1}).limit(5000):
                    sellers_list = doc.get('envolvedSellers', [])
                    if isinstance(sellers_list, list):
                        all_sellers.update(sellers_list)
                    elif sellers_list:
                        all_sellers.add(sellers_list)
        
        result = sorted(list(all_sellers))
        _ALL_SELLERS_CACHE = result
        if settings.DEBUG:
            print(f"Loaded {len(result)} unique sellers from sample (cached)")
        return result
    except Exception as e:
        if settings.DEBUG:
            print(f"Error getting sellers: {e}")
        _ALL_SELLERS_CACHE = []
        return []


def get_all_tags():
    """Get all unique tags from conversations metadata (cached)"""
    global _ALL_TAGS_CACHE
    
    if _ALL_TAGS_CACHE is not None:
        return _ALL_TAGS_CACHE
    
    try:
        collection = get_conversations_collection()
        all_tags = set()
        
        # Use aggregation with limit for performance
        pipeline = [
            {'$project': {'tags': '$metadata.clientTagsInput'}},
            {'$limit': 10000},  # Limit for performance
            {'$match': {'tags': {'$ne': None, '$ne': ''}}},
            {'$group': {'_id': '$tags'}}
        ]
        
        for doc in collection.aggregate(pipeline, allowDiskUse=True):
            tags = doc.get('_id')
            if tags:
                if isinstance(tags, str):
                    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                    all_tags.update(tag_list)
                elif isinstance(tags, list):
                    all_tags.update([str(t) for t in tags if t])
        
        result = sorted(list(all_tags))
        _ALL_TAGS_CACHE = result
        if settings.DEBUG:
            print(f"Loaded {len(result)} unique tags (cached)")
        return result
    except Exception as e:
        if settings.DEBUG:
            print(f"Error getting tags: {e}")
        _ALL_TAGS_CACHE = []
        return []


def get_all_sales_stages():
    """Get all unique sales stages from conversations (cached)"""
    global _ALL_SALES_STAGES_CACHE
    
    if _ALL_SALES_STAGES_CACHE is not None:
        return _ALL_SALES_STAGES_CACHE
    
    try:
        collection = get_conversations_collection()
        # Use distinct with a limit query for better performance
        stages = collection.distinct("metadata.salesStage", {"metadata.salesStage": {"$ne": None}})
        result = sorted([str(s) for s in stages if s])
        
        _ALL_SALES_STAGES_CACHE = result
        if settings.DEBUG:
            print(f"Loaded {len(result)} unique sales stages (cached)")
        return result
    except Exception as e:
        if settings.DEBUG:
            print(f"Error getting sales stages: {e}")
        _ALL_SALES_STAGES_CACHE = []
        return []


def get_uuid_to_email_mapping():
    """Get the uuidToEmail mapping from dicts database (cached)"""
    global _UUID_TO_EMAIL_CACHE
    
    # Return cached version if available
    if _UUID_TO_EMAIL_CACHE is not None:
        return _UUID_TO_EMAIL_CACHE
    
    # Load mapping from MongoDB
    try:
        client = get_mongodb_client()
        db = client['dicts']
        collection = db['dicts']
        
        # Find document with name "uuidToEmailDict" or "uuidToEmail"
        doc = collection.find_one({'name': 'uuidToEmailDict'})
        if not doc:
            doc = collection.find_one({'name': 'uuidToEmail'})
        
        if settings.DEBUG:
            print(f"Loading uuidToEmail mapping... Document found: {doc is not None}")
        
        if doc:
            # The mapping could be in 'dict' field or directly in the document
            if 'dict' in doc:
                mapping = doc['dict']
            elif 'value' in doc:
                mapping = doc['value']
            elif 'data' in doc:
                mapping = doc['data']
            else:
                # Try to use the document itself (excluding _id and name)
                mapping = {k: v for k, v in doc.items() if k not in ['_id', 'name']}
            
            if isinstance(mapping, dict):
                if settings.DEBUG:
                    print(f"UUID to email mapping loaded: {len(mapping)} entries")
                    # Show a sample mapping
                    if mapping:
                        sample_key = list(mapping.keys())[0]
                        print(f"Sample: {sample_key} -> {mapping[sample_key]}")
                # Cache the mapping
                _UUID_TO_EMAIL_CACHE = mapping
                return mapping
            elif isinstance(mapping, list):
                # If it's a list, convert to dict (assuming list of {uuid: email} objects)
                if settings.DEBUG:
                    print("Mapping is a list, attempting to convert...")
                result = {}
                for item in mapping:
                    if isinstance(item, dict):
                        # Could be {uuid: email} or {key: uuid, value: email}
                        if 'key' in item and 'value' in item:
                            result[item['key']] = item['value']
                        elif len(item) == 1:
                            result.update(item)
                if settings.DEBUG:
                    print(f"Converted list to dict with {len(result)} entries")
                # Cache the mapping
                _UUID_TO_EMAIL_CACHE = result
                return result
        
        if settings.DEBUG:
            print("No uuidToEmail mapping found or invalid format")
        # Cache empty dict to avoid repeated queries
        _UUID_TO_EMAIL_CACHE = {}
        return {}
    except Exception as e:
        # If there's an error, cache empty dict and return it
        import traceback
        if settings.DEBUG:
            print(f"Error getting uuidToEmail mapping: {e}")
            print(traceback.format_exc())
        _UUID_TO_EMAIL_CACHE = {}
        return {}


def map_seller_to_email(seller_uuid, uuid_to_email_map):
    """Map a seller UUID to email, or return UUID if no mapping exists"""
    if not seller_uuid:
        return seller_uuid
    
    # Try exact match first
    if seller_uuid in uuid_to_email_map:
        return uuid_to_email_map[seller_uuid]
    
    # Try case-insensitive match
    seller_lower = seller_uuid.lower()
    for key, value in uuid_to_email_map.items():
        if key.lower() == seller_lower:
            return value
    
    # No match found, return UUID
    return seller_uuid

