from pymongo import MongoClient, ASCENDING
import datetime
from bson.objectid import ObjectId
import logging
import re

# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Database:
    def __init__(self, connection_string="mongodb://localhost:27017/", email="user@example.com"):
        self.connection_string = connection_string
        self.email = email
        self.email_safe = email.replace('@', '_').replace('.', '_')
        self.client = None
        self.db = None
        self.user_collection = None
        self.tags_collection = None
        self.messages_collection = None
        self.timeview_collection = None
        self.projects = []
        self.connect()

    def connect(self):
        """Establish MongoDB connection and initialize collections."""
        try:
            self.client = MongoClient(self.connection_string)
            self.client.server_info()  # Test connection
            self.db = self.client["sarayu_db"]
            self.user_collection = self.db[f"user_{self.email_safe}"]
            self.tags_collection = self.db[f"tagcreated_{self.email_safe}"]
            self.messages_collection = self.db[f"mqttmessage_{self.email_safe}"]
            self.timeview_collection = self.db[f"timeview_messages_{self.email_safe}"]
            self._create_timeview_indexes()
            logging.info(f"Database initialized for {self.email}")
        except Exception as e:
            logging.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def is_connected(self):
        """Check if MongoDB connection is active."""
        if self.client is None:
            return False
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def reconnect(self):
        """Re-establish MongoDB connection if disconnected."""
        try:
            if self.client is not None:
                self.client.close()
            self.connect()
            logging.info("Reconnected to MongoDB")
        except Exception as e:
            logging.error(f"Failed to reconnect to MongoDB: {str(e)}")
            raise

    def _create_timeview_indexes(self):
        """Create indexes for timeview_messages collection."""
        try:
            self.timeview_collection.create_index([("topic", ASCENDING)])
            self.timeview_collection.create_index([("filename", ASCENDING)])
            self.timeview_collection.create_index([("frameIndex", ASCENDING)])
            self.timeview_collection.create_index([("topic", ASCENDING), ("filename", ASCENDING)])
            logging.info("Indexes created for timeview_messages collection")
        except Exception as e:
            logging.error(f"Failed to create indexes for timeview_messages: {str(e)}")

    def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
                self.client = None
                self.db = None
                self.user_collection = None
                self.tags_collection = None
                self.messages_collection = None
                self.timeview_collection = None
                logging.info("MongoDB connection closed")
            except Exception as e:
                logging.error(f"Error closing MongoDB connection: {str(e)}")

    def load_projects(self):
        """Load project names for the user."""
        self.projects.clear()
        try:
            for project in self.user_collection.find():
                project_name = project.get("project_name")
                if project_name and project_name not in self.projects:
                    self.projects.append(project_name)
            logging.info(f"Loaded projects: {self.projects}")
            return self.projects
        except Exception as e:
            logging.error(f"Error loading projects: {str(e)}")
            return []

    def create_project(self, project_name):
        """Create a new project."""
        if not project_name:
            return False, "Project name cannot be empty!"
        if self.user_collection.find_one({"project_name": project_name}):
            return False, "Project already exists!"
        
        project_data = {
            "project_name": project_name,
            "created_at": datetime.datetime.now().isoformat()
        }
        try:
            self.user_collection.insert_one(project_data)
            if project_name not in self.projects:
                self.projects.append(project_name)
            logging.info(f"Project {project_name} created")
            return True, f"Project {project_name} created successfully!"
        except Exception as e:
            logging.error(f"Failed to create project: {str(e)}")
            return False, f"Failed to create project: {str(e)}"

    def edit_project(self, old_project_name, new_project_name):
        """Rename a project and update related collections."""
        if new_project_name == old_project_name:
            return True, "No change made"
        if self.user_collection.find_one({"project_name": new_project_name}):
            return False, "Project already exists!"
        
        try:
            self.user_collection.update_one(
                {"project_name": old_project_name},
                {"$set": {"project_name": new_project_name}}
            )
            if old_project_name in self.projects:
                self.projects[self.projects.index(old_project_name)] = new_project_name
            self.tags_collection.update_many(
                {"project_name": old_project_name},
                {"$set": {"project_name": new_project_name}}
            )
            self.messages_collection.update_many(
                {"project_name": old_project_name},
                {"$set": {"project_name": new_project_name}}
            )
            self.timeview_collection.update_many(
                {"project_name": old_project_name},
                {"$set": {"project_name": new_project_name}}
            )
            logging.info(f"Project renamed from {old_project_name} to {new_project_name}")
            return True, f"Project renamed to {new_project_name} successfully!"
        except Exception as e:
            logging.error(f"Failed to edit project: {str(e)}")
            return False, f"Failed to edit project: {str(e)}"

    def delete_project(self, project_name):
        """Delete a project and its associated data."""
        try:
            self.user_collection.delete_one({"project_name": project_name})
            self.tags_collection.delete_many({"project_name": project_name})
            self.messages_collection.delete_many({"project_name": project_name})
            self.timeview_collection.delete_many({"project_name": project_name})
            if project_name in self.projects:
                self.projects.remove(project_name)
            logging.info(f"Project {project_name} deleted")
            return True, f"Project {project_name} deleted successfully!"
        except Exception as e:
            logging.error(f"Failed to delete project: {str(e)}")
            return False, f"Failed to delete project: {str(e)}"

    def get_project_data(self, project_name):
        """Retrieve data for a specific project."""
        try:
            data = self.user_collection.find_one({"project_name": project_name})
            logging.debug(f"Project data for {project_name}: {data}")
            return data
        except Exception as e:
            logging.error(f"Error fetching project data: {str(e)}")
            return None

    def parse_tag_string(self, tag_string):
        """Parse a tag string into a dictionary."""
        if not tag_string:
            logging.error("Tag cannot be empty!")
            return None
        return {"tag_name": tag_string}

    def add_tag(self, project_name, tag_data):
        """Add a tag to a project."""
        if not self.get_project_data(project_name):
            return False, "Project not found!"
        if self.tags_collection.find_one({"project_name": project_name, "tag_name": tag_data["tag_name"]}):
            return False, "Tag already exists in this project!"
        
        tag_data["project_name"] = project_name
        tag_data["created_at"] = datetime.datetime.now().isoformat()
        try:
            self.tags_collection.insert_one(tag_data)
            logging.info(f"Tag {tag_data['tag_name']} added to {project_name}")
            return True, "Tag added successfully!"
        except Exception as e:
            logging.error(f"Failed to add tag: {str(e)}")
            return False, f"Failed to add tag: {str(e)}"

    def edit_tag(self, project_name, row, new_tag_data):
        """Edit an existing tag."""
        tags = list(self.tags_collection.find({"project_name": project_name}))
        if row >= len(tags):
            return False, "Invalid tag index!"
        
        tag_id = tags[row]["_id"]
        current_tag_name = tags[row]["tag_name"]
        if new_tag_data["tag_name"] != current_tag_name and self.tags_collection.find_one(
            {"project_name": project_name, "tag_name": new_tag_data["tag_name"]}
        ):
            return False, "Tag already exists in this project!"
        
        new_tag_data["project_name"] = project_name
        new_tag_data["updated_at"] = datetime.datetime.now().isoformat()
        try:
            self.tags_collection.update_one(
                {"_id": tag_id},
                {"$set": new_tag_data}
            )
            self.messages_collection.update_many(
                {"project_name": project_name, "tag_name": current_tag_name},
                {"$set": {"tag_name": new_tag_data["tag_name"]}}
            )
            self.timeview_collection.update_many(
                {"project_name": project_name, "topic": current_tag_name},
                {"$set": {"topic": new_tag_data["tag_name"]}}
            )
            logging.info(f"Tag {current_tag_name} updated to {new_tag_data['tag_name']}")
            return True, "Tag updated successfully!"
        except Exception as e:
            logging.error(f"Failed to edit tag: {str(e)}")
            return False, f"Failed to edit tag: {str(e)}"

    def delete_tag(self, project_name, row):
        """Delete a tag from a project."""
        tags = list(self.tags_collection.find({"project_name": project_name}))
        if row >= len(tags):
            return False, "Invalid tag index!"
        
        tag_id = tags[row]["_id"]
        tag_name = tags[row]["tag_name"]
        try:
            self.tags_collection.delete_one({"_id": tag_id})
            self.messages_collection.delete_many({"project_name": project_name, "tag_name": tag_name})
            self.timeview_collection.delete_many({"project_name": project_name, "topic": tag_name})
            logging.info(f"Tag {tag_name} deleted from {project_name}")
            return True, "Tag deleted successfully!"
        except Exception as e:
            logging.error(f"Failed to delete tag: {str(e)}")
            return False, f"Failed to delete tag: {str(e)}"

    def update_tag_value(self, project_name, tag_name, values, timestamp=None):
        """Receive tag values without saving to messages_collection."""
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"
        
        tag = self.tags_collection.find_one({"project_name": project_name, "tag_name": tag_name})
        if not tag:
            logging.error(f"Tag {tag_name} not found for project {project_name}!")
            return False, "Tag not found!"
        
        timestamp_str = timestamp if timestamp else datetime.datetime.now().isoformat()
        logging.debug(f"Received {len(values)} values for {tag_name} in {project_name} at {timestamp_str}")
        return True, "Tag values received but not saved to mqttmessage collection"

    def get_tag_values(self, project_name, tag_name):
        """Retrieve tag values for a project."""
        try:
            messages = list(self.messages_collection.find(
                {"project_name": project_name, "tag_name": tag_name}
            ).sort("timestamp", 1))
            if not messages:
                logging.debug(f"No messages found for {tag_name} in {project_name}")
                return []
            
            for msg in messages:
                if "timestamp" not in msg or "values" not in msg:
                    logging.warning(f"Invalid message format for {tag_name}: {msg}")
                    msg["timestamp"] = msg.get("timestamp", datetime.datetime.now().isoformat())
                    msg["values"] = msg.get("values", [])
            
            logging.debug(f"Retrieved {len(messages)} messages for {tag_name} in {project_name}")
            return messages
        except Exception as e:
            logging.error(f"Error fetching tag values for {tag_name} in {project_name}: {str(e)}")
            return []

    def save_tag_values(self, project_name, tag_name, data):
        """Save tag values to messages_collection."""
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"
        
        tag = self.tags_collection.find_one({"project_name": project_name, "tag_name": tag_name})
        if not tag:
            logging.error(f"Tag {tag_name} not found for project {project_name}!")
            return False, "Tag not found!"
        
        message_data = {
            "_id": ObjectId(),
            "topic": tag_name,
            "values": data["values"],
            "project_name": project_name,
            "tag_name": tag_name,
            "timestamp": data["timestamp"]
        }
        try:
            result = self.messages_collection.insert_one(message_data)
            logging.debug(f"Saved {len(data['values'])} values for {tag_name} at {data['timestamp']}: {result.inserted_id}")
            return True, "Tag values saved successfully!"
        except Exception as e:
            logging.error(f"Error saving tag values for {tag_name}: {str(e)}")
            return False, f"Failed to save tag values: {str(e)}"

    def save_timeview_message(self, project_name, message_data):
        """Save a message for the timeview feature."""
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return False, "Project not found!"
        
        required_fields = ["topic", "filename", "frameIndex", "message"]
        for field in required_fields:
            if field not in message_data or message_data[field] is None:
                logging.error(f"Missing or invalid required field {field} in timeview message")
                return False, f"Missing or invalid required field: {field}"
        
        message_data.setdefault("numberOfChannels", 1)
        message_data.setdefault("samplingRate", None)
        message_data.setdefault("samplingSize", None)
        message_data.setdefault("messageFrequency", None)
        message_data.setdefault("createdAt", datetime.datetime.now().isoformat())
        
        message_data["project_name"] = project_name
        message_data["_id"] = ObjectId()
        
        try:
            result = self.timeview_collection.insert_one(message_data)
            logging.info(f"Saved timeview message for {message_data['topic']} in {project_name} with filename {message_data['filename']}: {result.inserted_id}")
            return True, "Timeview message saved successfully!"
        except Exception as e:
            logging.error(f"Error saving timeview message: {str(e)}")
            return False, f"Failed to save timeview message: {str(e)}"

    def get_timeview_messages(self, project_name, topic=None, filename=None):
        """Retrieve timeview messages, optionally filtered by topic and/or filename."""
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return []
        
        query = {"project_name": project_name}
        if topic:
            query["topic"] = topic
        if filename:
            query["filename"] = filename
        
        try:
            messages = list(self.timeview_collection.find(query).sort("createdAt", 1))
            if not messages:
                logging.debug(f"No timeview messages found for project {project_name}")
                return []
            
            logging.debug(f"Retrieved {len(messages)} timeview messages for project {project_name}")
            return messages
        except Exception as e:
            logging.error(f"Error fetching timeview messages: {str(e)}")
            return []

    def get_distinct_filenames(self, project_name):
        """Retrieve distinct filenames for a project from timeview_collection."""
        if not self.get_project_data(project_name):
            logging.error(f"Project {project_name} not found!")
            return []
        
        try:
            filenames = self.timeview_collection.distinct("filename", {"project_name": project_name})
            sorted_filenames = sorted(filenames, key=lambda x: int(re.match(r"data(\d+)", x).group(1)) if re.match(r"data(\d+)", x) else 0)
            logging.debug(f"Retrieved {len(sorted_filenames)} distinct filenames for project {project_name}")
            return sorted_filenames
        except Exception as e:
            logging.error(f"Error fetching distinct filenames: {str(e)}")
            return []