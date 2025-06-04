"""
MongoDB schema validation for lectures and notes collections
"""
import json

lectures_schema = {
    "bsonType": "object",
    "required": ["courseCode", "year", "quarter", "videoId", "videoUrl", "transcriptUrl", "status", "createdAt", "updatedAt"],
    "properties": {
        "courseCode": {"bsonType": "string"},
        "year": {"bsonType": "int"},
        "quarter": {"bsonType": "string"},
        "videoId": {"bsonType": "string"},
        "videoUrl": {"bsonType": "string"},
        "transcriptUrl": {"bsonType": "string"},
        "status": {
            "bsonType": "string",
            "enum": ["pending", "processing", "completed", "failed"]
        },
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"},
        "notesId": {"bsonType": ["objectId", "null"]},
        "error": {"bsonType": ["string", "null"]}
    }
}

notes_schema = {
    "bsonType": "object",
    "required": ["lectureId", "content", "format", "createdAt", "updatedAt"],
    "properties": {
        "lectureId": {"bsonType": "objectId"},
        "content": {"bsonType": "string"},
        "format": {"bsonType": "string"},
        "createdAt": {"bsonType": "date"},
        "updatedAt": {"bsonType": "date"}
    }
}

def get_schema_validation_commands():
    """
    Returns a list of commands to validate schemas
    """
    commands = []
    
    # Lectures collection validation
    commands.append({
        "collMod": "lectures",
        "validator": {
            "$jsonSchema": lectures_schema
        },
        "validationLevel": "moderate"
    })
    
    # Notes collection validation
    commands.append({
        "collMod": "notes",
        "validator": {
            "$jsonSchema": notes_schema
        },
        "validationLevel": "moderate"
    })
    
    return commands
