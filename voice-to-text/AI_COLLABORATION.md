# AI Collaboration Design
**Purpose:** Enable communication between Claude and Google Gemini via shared Google Drive file
**Version:** 1.0
**Date:** 2025-11-10

---

## Problem

When debugging Google Cloud-specific issues, it would be helpful for Claude to consult Google's Gemini AI directly for:
- Google Cloud internal knowledge
- Known issues with Google services
- Best practices from Google's perspective
- Quick answers to "does X work with Y?" questions

**Example Use Case (M4A debugging):**
- Claude spent 3+ hours debugging M4A batch_recognize
- Simple Google search "M4A batch not working" immediately revealed known issues
- Gemini (Google's AI) could have provided this answer instantly

---

## Solution: Shared File Communication

Use Google Drive shared file as message bus between Claude and Gemini.

### Architecture

```
┌─────────────┐                           ┌──────────────┐
│   Claude    │                           │   Gemini     │
│ (via Python)│                           │ (via GC UI)  │
└──────┬──────┘                           └──────┬───────┘
       │                                         │
       │  Write question                         │  Read question
       │  Read response                          │  Write response
       │                                         │
       └────────────► Google Drive ◄─────────────┘
                      ai_messages.json
```

### File Format: JSON Message Log

```json
{
  "metadata": {
    "created": "2025-11-10T10:00:00Z",
    "purpose": "Claude-Gemini communication channel",
    "version": "1.0"
  },
  "messages": [
    {
      "id": "msg_001",
      "thread_id": "thread_001",
      "timestamp": "2025-11-10T10:05:00Z",
      "source": "claude",
      "type": "question",
      "status": "pending",
      "content": {
        "question": "Does Google Speech-to-Text batch_recognize API support M4A format?",
        "context": {
          "issue": "Getting 'RecognitionAudio empty' error with M4A files",
          "tried": [
            "AutoDetectDecodingConfig - not supported",
            "ExplicitDecodingConfig with M4A_AAC encoding - still fails",
            "Correct sample_rate and audio_channel_count - still fails"
          ],
          "documentation_says": "M4A_AAC is listed in AudioEncoding enum"
        },
        "priority": "high",
        "expected_answer_type": "yes/no with explanation"
      }
    },
    {
      "id": "msg_002",
      "thread_id": "thread_001",
      "timestamp": "2025-11-10T10:15:00Z",
      "source": "gemini",
      "type": "response",
      "status": "completed",
      "content": {
        "answer": "No, M4A format has known issues with batch_recognize API.",
        "explanation": "While M4A_AAC is listed in documentation, it doesn't work reliably with batch operations. This is a known limitation.",
        "recommendation": "Convert to MP3 or WAV format before uploading.",
        "sources": [
          "Internal Google Cloud knowledge base",
          "Community forum discussions"
        ]
      }
    }
  ]
}
```

---

## Message Types

### 1. Question (Claude → Gemini)

```json
{
  "type": "question",
  "source": "claude",
  "status": "pending",
  "content": {
    "question": "...",
    "context": {...},
    "priority": "high|medium|low",
    "expected_answer_type": "yes/no|explanation|code|configuration"
  }
}
```

### 2. Response (Gemini → Claude)

```json
{
  "type": "response",
  "source": "gemini",
  "status": "completed",
  "content": {
    "answer": "...",
    "explanation": "...",
    "recommendation": "...",
    "sources": [...]
  }
}
```

### 3. Context Share (Either → Either)

```json
{
  "type": "context",
  "source": "claude|gemini",
  "content": {
    "project_state": "...",
    "current_issue": "...",
    "relevant_files": [...],
    "recent_changes": [...]
  }
}
```

### 4. Follow-up (Either → Either)

```json
{
  "type": "followup",
  "source": "claude|gemini",
  "thread_id": "thread_001",
  "content": {
    "question": "...",
    "references": ["msg_002"]
  }
}
```

---

## Implementation

### Phase 1: Basic Python Implementation (Claude Side)

```python
# app/services/ai_collaboration.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import json
import io
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class AICollaboration:
    """
    Enables communication between Claude and Gemini via shared Google Drive file.
    """

    def __init__(self, credentials_path: str, file_id: Optional[str] = None):
        """
        Initialize AI collaboration service.

        Args:
            credentials_path: Path to service account JSON credentials
            file_id: Google Drive file ID for ai_messages.json (if exists)
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        self.service = build('drive', 'v3', credentials=self.credentials)
        self.file_id = file_id

    def create_message_file(self, folder_id: Optional[str] = None) -> str:
        """
        Create new ai_messages.json file in Google Drive.

        Args:
            folder_id: Optional folder to create file in

        Returns:
            File ID of created file
        """
        initial_content = {
            "metadata": {
                "created": datetime.utcnow().isoformat() + "Z",
                "purpose": "Claude-Gemini communication channel",
                "version": "1.0"
            },
            "messages": []
        }

        file_metadata = {
            'name': 'ai_messages.json',
            'mimeType': 'application/json'
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Create file content
        media = MediaFileUpload(
            io.BytesIO(json.dumps(initial_content, indent=2).encode()),
            mimetype='application/json',
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        self.file_id = file.get('id')
        logger.info(f"Created ai_messages.json with ID: {self.file_id}")
        return self.file_id

    def read_messages(self) -> Dict:
        """
        Read all messages from shared file.

        Returns:
            Dict containing metadata and messages
        """
        request = self.service.files().get_media(fileId=self.file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_content.seek(0)
        return json.loads(file_content.read().decode())

    def write_message(self, message: Dict) -> None:
        """
        Append new message to shared file.

        Args:
            message: Message dict to append
        """
        # Read current content
        current_data = self.read_messages()

        # Add message ID if not present
        if 'id' not in message:
            message['id'] = f"msg_{len(current_data['messages']) + 1:03d}"

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.utcnow().isoformat() + "Z"

        # Append message
        current_data['messages'].append(message)

        # Write back
        media = MediaFileUpload(
            io.BytesIO(json.dumps(current_data, indent=2).encode()),
            mimetype='application/json',
            resumable=True
        )

        self.service.files().update(
            fileId=self.file_id,
            media_body=media
        ).execute()

        logger.info(f"Wrote message {message['id']} to ai_messages.json")

    def ask_gemini(
        self,
        question: str,
        context: Dict = None,
        priority: str = "medium",
        thread_id: Optional[str] = None
    ) -> str:
        """
        Post question for Gemini to answer.

        Args:
            question: Question to ask
            context: Additional context dict
            priority: Priority level (high, medium, low)
            thread_id: Optional thread ID for follow-ups

        Returns:
            Message ID of posted question
        """
        if thread_id is None:
            # Generate new thread ID
            current_data = self.read_messages()
            thread_count = len(set(m.get('thread_id', '') for m in current_data['messages']))
            thread_id = f"thread_{thread_count + 1:03d}"

        message = {
            "thread_id": thread_id,
            "source": "claude",
            "type": "question",
            "status": "pending",
            "content": {
                "question": question,
                "context": context or {},
                "priority": priority,
                "expected_answer_type": "explanation"
            }
        }

        self.write_message(message)
        return message.get('id', '')

    def check_responses(self, thread_id: Optional[str] = None) -> List[Dict]:
        """
        Check for responses from Gemini.

        Args:
            thread_id: Optional thread ID to filter responses

        Returns:
            List of response messages
        """
        current_data = self.read_messages()
        responses = [
            m for m in current_data['messages']
            if m.get('source') == 'gemini' and m.get('type') == 'response'
        ]

        if thread_id:
            responses = [r for r in responses if r.get('thread_id') == thread_id]

        return responses

    def get_pending_questions(self) -> List[Dict]:
        """
        Get all pending questions (for Gemini to answer).

        Returns:
            List of pending question messages
        """
        current_data = self.read_messages()
        return [
            m for m in current_data['messages']
            if m.get('type') == 'question' and m.get('status') == 'pending'
        ]
```

---

## Usage Examples

### Example 1: Ask Gemini About M4A Support

```python
# In transcribe_v2.py, when getting repeated errors
from app.services.ai_collaboration import AICollaboration

collab = AICollaboration(
    credentials_path="/path/to/service-account.json",
    file_id="<google-drive-file-id>"
)

# Claude asks Gemini
message_id = collab.ask_gemini(
    question="Does Google Speech-to-Text batch_recognize API support M4A format?",
    context={
        "issue": "Getting 'RecognitionAudio empty' error with M4A files",
        "tried": [
            "AutoDetectDecodingConfig - not supported",
            "ExplicitDecodingConfig with M4A_AAC encoding - still fails"
        ],
        "documentation_says": "M4A_AAC is listed in AudioEncoding enum"
    },
    priority="high"
)

logger.info(f"Posted question to Gemini: {message_id}")
logger.info("User will check Gemini and post response to shared file")
```

### Example 2: Gemini's Workflow (Manual for now)

1. User opens Google Drive
2. Opens `ai_messages.json`
3. Copies pending question
4. Pastes into Gemini chat in Google Cloud Console
5. Gets Gemini's response
6. Manually adds response to `ai_messages.json`:

```json
{
  "id": "msg_002",
  "thread_id": "thread_001",
  "timestamp": "2025-11-10T10:15:00Z",
  "source": "gemini",
  "type": "response",
  "status": "completed",
  "content": {
    "answer": "No, M4A format has known issues with batch_recognize API.",
    "explanation": "While M4A_AAC is listed in documentation, it doesn't work reliably with batch operations.",
    "recommendation": "Convert to MP3 or WAV format before uploading."
  }
}
```

### Example 3: Claude Checks for Response

```python
# Check for responses periodically
responses = collab.check_responses(thread_id="thread_001")

for response in responses:
    if response['status'] == 'completed':
        logger.info(f"Gemini answered: {response['content']['answer']}")
        logger.info(f"Recommendation: {response['content']['recommendation']}")
```

---

## Benefits

1. **Direct Google Knowledge:** Gemini has Google-internal knowledge about Cloud services
2. **Known Issues:** Can quickly identify documented bugs and limitations
3. **Best Practices:** Google's recommended approaches
4. **Bidirectional:** Both AIs can ask questions of each other
5. **Traceable:** Full conversation history in JSON
6. **Async:** Neither AI blocks waiting for other

---

## Limitations

1. **Manual Gemini Side:** Initially requires user to manually copy questions to Gemini
2. **No Real-time:** File-based, not instant messaging
3. **Polling Required:** Need to periodically check for responses
4. **No Notification:** No push notifications when response ready

---

## Future Enhancements

### Phase 2: Automated Gemini Integration
- If Gemini API becomes available, automate Gemini side
- Gemini reads questions and writes responses automatically

### Phase 3: Real-time Communication
- Use Google Drive API's changes.watch() for push notifications
- WebSocket or Server-Sent Events for real-time updates

### Phase 4: Multi-AI Collaboration
- Add more AIs to conversation (GPT-4, etc.)
- Structured debate and consensus building

---

## Setup Instructions

### 1. Create Shared File

```bash
# Run once to create ai_messages.json in Google Drive
python -c "
from app.services.ai_collaboration import AICollaboration
collab = AICollaboration('/path/to/service-account.json')
file_id = collab.create_message_file()
print(f'Created file ID: {file_id}')
"
```

### 2. Share File with User

```bash
# Get shareable link
gcloud storage objects describe gs://bucket-name/ai_messages.json
```

### 3. Configure Environment

```bash
# Add to .env
AI_COLLAB_FILE_ID=<file-id-from-step-1>
```

### 4. Test Communication

```python
# Test asking a question
from app.services.ai_collaboration import AICollaboration
import os

collab = AICollaboration(
    credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    file_id=os.getenv("AI_COLLAB_FILE_ID")
)

collab.ask_gemini(
    question="Is this communication channel working?",
    priority="low"
)

print("Question posted! Check Google Drive file in browser.")
```

---

## Decision Point

**Question for John:** Should we implement this now, or is it more of an experiment to try later?

**Considerations:**
- **Pros:** Could speed up Google Cloud debugging significantly
- **Cons:** Adds complexity, manual workflow initially
- **Effort:** ~1-2 hours to implement basic version
- **Value:** High if we encounter more Google-specific issues

**Recommendation:** Implement Phase 1 (basic Python side) now. Test with 1-2 questions to see if valuable. Iterate based on experience.

---

**End of AI Collaboration Design**
