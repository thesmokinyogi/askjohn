#!/usr/bin/env python3
"""
OBSERVATION: How does proto-plus dict conversion actually work?

Questions to answer:
1. What does dict(location_object) produce?
2. Is 'metadata' nested as a proto-plus object or already a dict?
3. Do nested objects auto-convert or need manual dict() calls?
4. What's the actual structure we're working with?
"""

import os
import json
from google.cloud.speech_v2 import SpeechClient
from google.cloud.location import locations_pb2

# Get project ID
project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
if not project_id:
    print("ERROR: GOOGLE_CLOUD_PROJECT not set")
    exit(1)

print(f"Project: {project_id}\n")
print("=" * 80)
print("OBSERVING: Proto-plus dict conversion behavior")
print("=" * 80)

# Create client and query locations
client = SpeechClient()
request = locations_pb2.ListLocationsRequest(name=f"projects/{project_id}")
response = client.list_locations(request=request)

print(f"\nTotal locations returned: {len(response.locations)}")

# Examine FIRST location in detail
loc = response.locations[0]

print("\n" + "=" * 80)
print(f"EXAMINING: {loc.location_id}")
print("=" * 80)

# OBSERVATION 1: What type is the location object?
print("\n1. Location object type:")
print(f"   type(loc) = {type(loc)}")
print(f"   type(loc).__name__ = {type(loc).__name__}")

# OBSERVATION 2: What does dict(loc) produce?
print("\n2. Converting location to dict:")
try:
    loc_dict = dict(loc)
    print(f"   ✓ dict(loc) succeeded")
    print(f"   Keys in loc_dict: {list(loc_dict.keys())}")
except Exception as e:
    print(f"   ✗ dict(loc) failed: {e}")
    loc_dict = None

# OBSERVATION 3: What's in the 'metadata' field?
if loc_dict:
    print("\n3. Examining 'metadata' field:")
    metadata = loc_dict.get('metadata')
    print(f"   type(metadata) = {type(metadata)}")
    print(f"   Is dict? {isinstance(metadata, dict)}")

    if metadata:
        print(f"   Keys in metadata: {list(metadata.keys())[:10]}")  # First 10 keys

        # OBSERVATION 4: What's in 'languages'?
        if 'languages' in metadata:
            print("\n4. Examining 'languages' field:")
            languages = metadata['languages']
            print(f"   type(languages) = {type(languages)}")
            print(f"   Is dict? {isinstance(languages, dict)}")

            if isinstance(languages, dict):
                print(f"   Language codes: {list(languages.keys())}")

                # OBSERVATION 5: Pick one language and examine structure
                if languages:
                    first_lang = list(languages.keys())[0]
                    lang_data = languages[first_lang]
                    print(f"\n5. Examining language '{first_lang}':")
                    print(f"   type(lang_data) = {type(lang_data)}")
                    print(f"   Is dict? {isinstance(lang_data, dict)}")

                    if isinstance(lang_data, dict):
                        print(f"   Keys: {list(lang_data.keys())}")

                        # OBSERVATION 6: Examine models
                        if 'models' in lang_data:
                            models = lang_data['models']
                            print(f"\n6. Examining 'models' field:")
                            print(f"   type(models) = {type(models)}")
                            print(f"   Is dict? {isinstance(models, dict)}")

                            if isinstance(models, dict):
                                model_ids = list(models.keys())[:5]  # First 5
                                print(f"   Model IDs (first 5): {model_ids}")

                                # OBSERVATION 7: Examine one model's structure
                                if models:
                                    first_model = list(models.keys())[0]
                                    model_data = models[first_model]
                                    print(f"\n7. Examining model '{first_model}':")
                                    print(f"   type(model_data) = {type(model_data)}")
                                    print(f"   Is dict? {isinstance(model_data, dict)}")

                                    if isinstance(model_data, dict):
                                        print(f"   Keys: {list(model_data.keys())}")

                                        # Show full structure of first model (formatted)
                                        print(f"\n   Full structure:")
                                        print(f"   {json.dumps(model_data, indent=6, default=str)[:500]}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("Based on observations above:")
print("- Does dict(proto_plus_obj) recursively convert nested objects?")
print("- Can we use standard Python dict operations (.get(), .keys(), etc.)?")
print("- What's the exact data structure we're parsing?")
print("\nReview the output above to answer these questions.")
