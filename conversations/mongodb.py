"""
MongoDB connection and utility functions
"""
from pymongo import MongoClient
from django.conf import settings


def get_mongodb_client():
    """Get MongoDB client connection"""
    return MongoClient(settings.MONGODB_URI)


def get_conversations_collection():
    """Get the conversations collection from MongoDB"""
    client = get_mongodb_client()
    db = client[settings.MONGODB_DB_NAME]
    return db[settings.MONGODB_COLLECTION_NAME]


def get_all_sellers():
    """Get all unique seller IDs from conversations"""
    collection = get_conversations_collection()
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

