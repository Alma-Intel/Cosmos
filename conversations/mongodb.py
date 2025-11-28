"""
MongoDB connection and utility functions
"""
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
from django.conf import settings


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
    """Get all unique seller IDs from conversations"""
    collection = get_conversations_collection()
    # Check if collection is empty
    if collection.count_documents({}) == 0:
        return []
    
    sellers = collection.distinct("envolvedSellers")
    # Flatten the array and get unique values
    all_sellers = set()
    for seller_list in sellers:
        if isinstance(seller_list, list):
            all_sellers.update(seller_list)
        else:
            all_sellers.add(seller_list)
    return sorted(list(all_sellers))


def get_all_tags():
    """Get all unique tags from conversations metadata"""
    collection = get_conversations_collection()
    # Get all conversations and extract tags
    all_tags = set()
    for conv in collection.find({}, {"metadata.clientTagsInput": 1}):
        tags = conv.get("metadata", {}).get("clientTagsInput")
        if tags:
            if isinstance(tags, str):
                # If tags is a string, split by comma
                tag_list = [tag.strip() for tag in tags.split(",")]
                all_tags.update(tag_list)
            elif isinstance(tags, list):
                all_tags.update(tags)
    return sorted(list(all_tags))


def get_all_sales_stages():
    """Get all unique sales stages from conversations"""
    collection = get_conversations_collection()
    stages = collection.distinct("metadata.salesStage")
    # Filter out None values and convert to strings
    return sorted([str(s) for s in stages if s])


def get_uuid_to_email_mapping():
    """Get the uuidToEmail mapping from dicts database"""
    try:
        client = get_mongodb_client()
        db = client['dicts']
        collection = db['dicts']
        
        # Find document with name "uuidToEmail"
        doc = collection.find_one({'name': 'uuidToEmail'})
        
        if doc and 'dict' in doc:
            # Return the dict mapping UUIDs to emails
            return doc['dict']
        return {}
    except Exception as e:
        # If there's an error, return empty dict
        if settings.DEBUG:
            print(f"Error getting uuidToEmail mapping: {e}")
        return {}


def map_seller_to_email(seller_uuid, uuid_to_email_map):
    """Map a seller UUID to email, or return UUID if no mapping exists"""
    return uuid_to_email_map.get(seller_uuid, seller_uuid)

