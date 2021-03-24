import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)
EMAIL_TEMPLATES_PATH = os.path.join(PROJECT_ROOT, "templates", "email")
EMAIL_MESSAGES_PATH = os.path.join(EMAIL_TEMPLATES_PATH, "messages")
EMAIL_PLAIN_MESSAGES_PATH = os.path.join(EMAIL_TEMPLATES_PATH, "plain_messages")
EMAIL_GENERATED_PATH = os.path.join(EMAIL_TEMPLATES_PATH, "generated")
