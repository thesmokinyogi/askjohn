"""
AI Collaboration Service

Enables communication between Claude and Google Gemini via shared Google Drive file.
Uses JSON file as message bus for asynchronous AI-to-AI communication.

Example Usage:
    collab = AICollaboration(
        credentials_path="/path/to/service-account.json",
        file_id="google-drive-file-id"
    )

    # Claude asks question
    msg_id = collab.ask_gemini(
        question="Does batch_recognize support M4A?",
        context={"error": "RecognitionAudio empty"},
        priority="high"
    )

    # Check for responses later
    responses = collab.check_responses()
    for r in responses:
        print(r['content']['answer'])
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import json
import io
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class AICollaboration:
    """
    Enables communication between Claude and Gemini via shared Google Drive file.

    Uses JSON file in Google Drive as message bus. Claude writes questions,
    Gemini (via user) writes responses. Both can read full message history.

    Attributes:
        credentials: Google service account credentials
        service: Google Drive API service
        file_id: Google Drive file ID for ai_messages.json
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

        Example:
            file_id = collab.create_message_file()
            print(f"Created file: {file_id}")
        """
        initial_content = {
            "metadata": {
                "created": datetime.utcnow().isoformat() + "Z",
                "purpose": "Claude-Gemini communication channel",
                "version": "1.0",
                "participants": ["claude", "gemini"]
            },
            "messages": []
        }

        file_metadata = {
            'name': 'ai_messages.json',
            'mimeType': 'application/json',
            'description': 'AI collaboration message bus for Claude-Gemini communication'
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Create file content in memory
        content_bytes = json.dumps(initial_content, indent=2).encode()
        media = MediaIoBaseUpload(
            io.BytesIO(content_bytes),
            mimetype='application/json',
            resumable=True
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink'
        ).execute()

        self.file_id = file.get('id')
        logger.info(f"Created ai_messages.json with ID: {self.file_id}")
        logger.info(f"View at: {file.get('webViewLink')}")
        return self.file_id

    def read_messages(self) -> Dict:
        """
        Read all messages from shared file.

        Returns:
            Dict containing metadata and messages

        Raises:
            Exception: If file_id not set or file not found

        Example:
            data = collab.read_messages()
            print(f"Total messages: {len(data['messages'])}")
        """
        if not self.file_id:
            raise ValueError("file_id not set. Create file first or provide file_id in constructor.")

        request = self.service.files().get_media(fileId=self.file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_content.seek(0)
        return json.loads(file_content.read().decode())

    def write_message(self, message: Dict) -> str:
        """
        Append new message to shared file.

        Args:
            message: Message dict to append (must have source, type, content)

        Returns:
            Message ID of written message

        Example:
            msg_id = collab.write_message({
                "source": "claude",
                "type": "question",
                "content": {"question": "..."}
            })
        """
        # Validate message structure
        required_fields = ['source', 'type', 'content']
        for field in required_fields:
            if field not in message:
                raise ValueError(f"Message missing required field: {field}")

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
        content_bytes = json.dumps(current_data, indent=2).encode()
        media = MediaIoBaseUpload(
            io.BytesIO(content_bytes),
            mimetype='application/json',
            resumable=True
        )

        self.service.files().update(
            fileId=self.file_id,
            media_body=media
        ).execute()

        logger.info(f"Wrote message {message['id']} to ai_messages.json")
        return message['id']

    def ask_gemini(
        self,
        question: str,
        context: Optional[Dict] = None,
        priority: str = "medium",
        thread_id: Optional[str] = None,
        expected_answer_type: str = "explanation"
    ) -> str:
        """
        Post question for Gemini to answer.

        Args:
            question: Question to ask Gemini
            context: Additional context dict (issue, error, tried approaches, etc.)
            priority: Priority level (high, medium, low)
            thread_id: Optional thread ID for follow-ups
            expected_answer_type: Type of answer expected (yes/no, explanation, code, etc.)

        Returns:
            Message ID of posted question

        Example:
            msg_id = collab.ask_gemini(
                question="Does batch_recognize support M4A?",
                context={
                    "error": "RecognitionAudio empty",
                    "tried": ["AutoDetectDecodingConfig", "ExplicitDecodingConfig"]
                },
                priority="high"
            )
        """
        if thread_id is None:
            # Generate new thread ID
            current_data = self.read_messages()
            existing_threads = set(m.get('thread_id', '') for m in current_data['messages'])
            thread_id = f"thread_{len(existing_threads) + 1:03d}"

        message = {
            "thread_id": thread_id,
            "source": "claude",
            "type": "question",
            "status": "pending",
            "content": {
                "question": question,
                "context": context or {},
                "priority": priority,
                "expected_answer_type": expected_answer_type
            }
        }

        message_id = self.write_message(message)
        logger.info(f"Posted question to Gemini (thread {thread_id}): {question}")
        return message_id

    def check_responses(
        self,
        thread_id: Optional[str] = None,
        since_message_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Check for responses from Gemini.

        Args:
            thread_id: Optional thread ID to filter responses
            since_message_id: Optional message ID to get only newer responses

        Returns:
            List of response messages

        Example:
            responses = collab.check_responses(thread_id="thread_001")
            for r in responses:
                print(f"Answer: {r['content']['answer']}")
        """
        current_data = self.read_messages()
        responses = [
            m for m in current_data['messages']
            if m.get('source') == 'gemini' and m.get('type') == 'response'
        ]

        # Filter by thread if specified
        if thread_id:
            responses = [r for r in responses if r.get('thread_id') == thread_id]

        # Filter by message ID if specified
        if since_message_id:
            start_index = None
            for i, m in enumerate(current_data['messages']):
                if m.get('id') == since_message_id:
                    start_index = i
                    break
            if start_index is not None:
                responses = [r for r in responses if current_data['messages'].index(r) > start_index]

        return responses

    def get_pending_questions(self) -> List[Dict]:
        """
        Get all pending questions (for Gemini to answer).

        Useful for user to see what questions are waiting for Gemini.

        Returns:
            List of pending question messages

        Example:
            pending = collab.get_pending_questions()
            print(f"{len(pending)} questions pending")
        """
        current_data = self.read_messages()
        return [
            m for m in current_data['messages']
            if m.get('type') == 'question' and m.get('status') == 'pending'
        ]

    def mark_question_answered(self, question_id: str) -> None:
        """
        Mark a question as answered (called after response received).

        Args:
            question_id: Message ID of question to mark

        Example:
            collab.mark_question_answered("msg_001")
        """
        current_data = self.read_messages()

        # Find and update question
        for message in current_data['messages']:
            if message.get('id') == question_id and message.get('type') == 'question':
                message['status'] = 'answered'
                break

        # Write back
        content_bytes = json.dumps(current_data, indent=2).encode()
        media = MediaIoBaseUpload(
            io.BytesIO(content_bytes),
            mimetype='application/json',
            resumable=True
        )

        self.service.files().update(
            fileId=self.file_id,
            media_body=media
        ).execute()

        logger.info(f"Marked question {question_id} as answered")

    def get_conversation_summary(self) -> Dict:
        """
        Get summary statistics about the conversation.

        Returns:
            Dict with counts of messages, threads, pending questions, etc.

        Example:
            summary = collab.get_conversation_summary()
            print(f"Total messages: {summary['total_messages']}")
            print(f"Pending questions: {summary['pending_questions']}")
        """
        current_data = self.read_messages()
        messages = current_data['messages']

        threads = set(m.get('thread_id', '') for m in messages)
        questions = [m for m in messages if m.get('type') == 'question']
        responses = [m for m in messages if m.get('type') == 'response']
        pending = [m for m in questions if m.get('status') == 'pending']

        return {
            'total_messages': len(messages),
            'total_threads': len(threads),
            'total_questions': len(questions),
            'total_responses': len(responses),
            'pending_questions': len(pending),
            'claude_messages': len([m for m in messages if m.get('source') == 'claude']),
            'gemini_messages': len([m for m in messages if m.get('source') == 'gemini']),
            'created': current_data['metadata'].get('created'),
        }


# CLI utility functions for testing

def create_collab_file(credentials_path: str) -> str:
    """
    CLI utility to create ai_messages.json file.

    Args:
        credentials_path: Path to service account credentials

    Returns:
        File ID of created file
    """
    collab = AICollaboration(credentials_path)
    file_id = collab.create_message_file()
    print(f"✅ Created ai_messages.json")
    print(f"📄 File ID: {file_id}")
    print(f"\n🔧 Add to .env:")
    print(f"AI_COLLAB_FILE_ID={file_id}")
    return file_id


def test_communication(credentials_path: str, file_id: str) -> None:
    """
    CLI utility to test communication channel.

    Args:
        credentials_path: Path to service account credentials
        file_id: Google Drive file ID
    """
    collab = AICollaboration(credentials_path, file_id)

    print("🧪 Testing AI collaboration channel...")

    # Post test question
    msg_id = collab.ask_gemini(
        question="Is this communication channel working?",
        context={"test": "initial test message"},
        priority="low"
    )

    print(f"✅ Posted test question: {msg_id}")
    print(f"\n📝 Next steps:")
    print(f"1. Open Google Drive and find ai_messages.json")
    print(f"2. Open in browser or download")
    print(f"3. You should see pending question from Claude")
    print(f"4. Copy question to Gemini in Google Cloud Console")
    print(f"5. Add Gemini's response to the JSON file")

    # Show summary
    summary = collab.get_conversation_summary()
    print(f"\n📊 Conversation Summary:")
    print(f"   Total messages: {summary['total_messages']}")
    print(f"   Pending questions: {summary['pending_questions']}")


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ai_collaboration.py create <credentials-path>")
        print("  python ai_collaboration.py test <credentials-path> <file-id>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("Error: credentials-path required")
            sys.exit(1)
        create_collab_file(sys.argv[2])

    elif command == "test":
        if len(sys.argv) < 4:
            print("Error: credentials-path and file-id required")
            sys.exit(1)
        test_communication(sys.argv[2], sys.argv[3])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
