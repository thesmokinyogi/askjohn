#!/usr/bin/env python3
"""
Demo: AI Collaboration Between Claude and Gemini

This script demonstrates how Claude can communicate with Google's Gemini AI
via a shared Google Drive file.

Usage:
    # Step 1: Create the shared file
    python demo_ai_collab.py create

    # Step 2: Test communication
    python demo_ai_collab.py test

    # Step 3: Ask a real question
    python demo_ai_collab.py ask "Does batch_recognize support M4A?"

    # Step 4: Check for responses
    python demo_ai_collab.py check
"""

import os
import sys
from app.services.ai_collaboration import AICollaboration
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
FILE_ID = os.getenv("AI_COLLAB_FILE_ID")


def create_file():
    """Create new ai_messages.json file in Google Drive."""
    if not CREDENTIALS_PATH:
        print("❌ Error: GOOGLE_APPLICATION_CREDENTIALS not set in .env")
        sys.exit(1)

    print("🚀 Creating ai_messages.json in Google Drive...")
    collab = AICollaboration(CREDENTIALS_PATH)
    file_id = collab.create_message_file()

    print(f"\n✅ Success! File created.")
    print(f"📄 File ID: {file_id}")
    print(f"\n🔧 Add this to your .env file:")
    print(f"AI_COLLAB_FILE_ID={file_id}")
    print(f"\n📝 Next steps:")
    print(f"1. Add AI_COLLAB_FILE_ID to .env")
    print(f"2. Run: python demo_ai_collab.py test")


def test_communication():
    """Post test question to verify communication channel works."""
    if not FILE_ID:
        print("❌ Error: AI_COLLAB_FILE_ID not set in .env")
        print("Run: python demo_ai_collab.py create")
        sys.exit(1)

    print("🧪 Testing AI collaboration channel...")
    collab = AICollaboration(CREDENTIALS_PATH, FILE_ID)

    # Post test question
    msg_id = collab.ask_gemini(
        question="Is this communication channel working? Please respond with 'Yes, working!' if you can read this.",
        context={
            "test": "initial test message",
            "from": "Claude via demo_ai_collab.py"
        },
        priority="low"
    )

    print(f"✅ Posted test question: {msg_id}")

    # Show summary
    summary = collab.get_conversation_summary()
    print(f"\n📊 Conversation Summary:")
    print(f"   Total messages: {summary['total_messages']}")
    print(f"   Total threads: {summary['total_threads']}")
    print(f"   Pending questions: {summary['pending_questions']}")

    print(f"\n📝 Next steps:")
    print(f"1. Go to Google Drive: https://drive.google.com")
    print(f"2. Search for 'ai_messages.json'")
    print(f"3. Open the file")
    print(f"4. Find the pending question from Claude")
    print(f"5. Copy the question")
    print(f"6. Go to Google Cloud Console: https://console.cloud.google.com")
    print(f"7. Open Gemini AI chat")
    print(f"8. Paste the question")
    print(f"9. Get Gemini's response")
    print(f"10. Add response to ai_messages.json (see example below)")

    print(f"\n💡 Example response to add:")
    print("""
{
  "thread_id": "thread_001",
  "source": "gemini",
  "type": "response",
  "status": "completed",
  "content": {
    "answer": "Yes, working!",
    "explanation": "I can read messages from the shared Google Drive file."
  }
}
    """)


def ask_question(question: str):
    """Ask Gemini a specific question."""
    if not FILE_ID:
        print("❌ Error: AI_COLLAB_FILE_ID not set in .env")
        sys.exit(1)

    print(f"❓ Asking Gemini: {question}")
    collab = AICollaboration(CREDENTIALS_PATH, FILE_ID)

    msg_id = collab.ask_gemini(
        question=question,
        priority="medium"
    )

    print(f"✅ Posted question: {msg_id}")
    print(f"\n📝 User should now:")
    print(f"1. Open ai_messages.json in Google Drive")
    print(f"2. Find question {msg_id}")
    print(f"3. Copy to Gemini in Google Cloud Console")
    print(f"4. Add Gemini's response to the file")
    print(f"\nThen run: python demo_ai_collab.py check")


def check_responses():
    """Check for responses from Gemini."""
    if not FILE_ID:
        print("❌ Error: AI_COLLAB_FILE_ID not set in .env")
        sys.exit(1)

    print("🔍 Checking for responses from Gemini...")
    collab = AICollaboration(CREDENTIALS_PATH, FILE_ID)

    # Show summary
    summary = collab.get_conversation_summary()
    print(f"\n📊 Conversation Summary:")
    print(f"   Total messages: {summary['total_messages']}")
    print(f"   Total questions: {summary['total_questions']}")
    print(f"   Total responses: {summary['total_responses']}")
    print(f"   Pending questions: {summary['pending_questions']}")

    # Show pending questions
    pending = collab.get_pending_questions()
    if pending:
        print(f"\n⏳ Pending Questions ({len(pending)}):")
        for q in pending:
            print(f"   • [{q['id']}] {q['content']['question']}")

    # Show responses
    responses = collab.check_responses()
    if responses:
        print(f"\n✅ Responses from Gemini ({len(responses)}):")
        for r in responses:
            print(f"\n   Thread: {r.get('thread_id')}")
            print(f"   Message: {r.get('id')}")
            print(f"   Answer: {r['content'].get('answer', 'N/A')}")
            if 'explanation' in r['content']:
                print(f"   Explanation: {r['content']['explanation']}")
            if 'recommendation' in r['content']:
                print(f"   Recommendation: {r['content']['recommendation']}")
    else:
        print(f"\n⏳ No responses yet from Gemini.")
        print(f"   User needs to manually add responses to ai_messages.json")


def show_help():
    """Show usage help."""
    print(__doc__)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        create_file()

    elif command == "test":
        test_communication()

    elif command == "ask":
        if len(sys.argv) < 3:
            print("❌ Error: Question required")
            print("Usage: python demo_ai_collab.py ask \"Your question here\"")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        ask_question(question)

    elif command == "check":
        check_responses()

    elif command == "help":
        show_help()

    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
