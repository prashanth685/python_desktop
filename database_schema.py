from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime


class UserCollectionSchema:
    """Schema for user_collection (user_<email_safe>)"""
    def __init__(self):
        self.project_name: str
        self.created_at: str  # ISO format datetime string

class TagCollectionSchema:
    """Schema for tags_collection (tagcreated_<email_safe>)"""
    def __init__(self):
        self._id: ObjectId
        self.project_name: str
        self.tag_name: str
        self.created_at: str  # ISO format datetime string
        self.updated_at: Optional[str]  # ISO format datetime string

class MessageCollectionSchema:
    """Schema for messages_collection (mqttmessage_<email_safe>)"""
    def __init__(self):
        self._id: ObjectId
        self.project_name: str
        self.tag_name: str
        self.topic: str
        self.values: List[Any]
        self.timestamp: str  # ISO format datetime string

class TimeviewCollectionSchema:
    """Schema for timeview_collection (timeview_messages_<email_safe>)"""
    def __init__(self):
        self._id: ObjectId
        self.project_name: str
        self.topic: str
        self.filename: str
        self.frameIndex: int
        self.message: Dict[str, Any]
        self.numberOfChannels: Optional[int]
        self.samplingRate: Optional[float]
        self.samplingSize: Optional[int]
        self.messageFrequency: Optional[float]
        self.createdAt: str  # ISO format datetime string
        self.updatedAt: str  # ISO format datetime string

# Example usage of schema definitions
def get_collection_schemas() -> Dict[str, Any]:
    """Returns a dictionary of collection names and their schema definitions"""
    return {
        "user_collection": {
            "name": "user_<email_safe>",
            "schema": UserCollectionSchema,
            "description": "Stores project information for a user",
            "indexes": []
        },
        "tags_collection": {
            "name": "tagcreated_<email_safe>",
            "schema": TagCollectionSchema,
            "description": "Stores tag information for projects",
            "indexes": []
        },
        "messages_collection": {
            "name": "mqttmessage_<email_safe>",
            "schema": MessageCollectionSchema,
            "description": "Stores MQTT message data",
            "indexes": []
        },
        "timeview_collection": {
            "name": "timeview_messages_<email_safe>",
            "schema": TimeviewCollectionSchema,
            "description": "Stores timeview feature messages",
            "indexes": [
                [("topic", "ASCENDING")],
                [("filename", "ASCENDING")],
                [("frameIndex", "ASCENDING")],
                [("topic", "ASCENDING"), ("filename", "ASCENDING")]
            ]
        }
    }