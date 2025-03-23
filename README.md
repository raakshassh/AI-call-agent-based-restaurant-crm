AI Call Agent-Based Restaurant CRM

A Flask-based application that uses voice interactions to provide restaurant information and process reservations. The system integrates Twilio for voice calls, Gemini Flash for speech recognition and generation, and Google Calendar for managing reservations—all while logging interactions for future reference.

Features

- Intelligent Call Handling: Manage customer inquiries and reservations using AI-driven voice recognition.
- Automated Reservations: Capture booking details and log them into reservations.log.
- Conversation Tracking: Maintain detailed records of conversations in restaurant_conversations.log.
- Customizable: Tailor the AI agent to match your restaurant's tone and operational needs.
- Scalable: Integrate with existing CRM systems for expanded functionality.

Requirements

- Python 3.8 or higher
- Dependencies from requirements.txt

Installation

Get started in just a few steps:

1. Clone the Repository:
   git clone https://github.com/raakshassh/ai-call-agent-based-restaurant-crm.git
   
   cd ai-call-agent-based-restaurant-crm

3. Install Dependencies:
   pip install -r requirements.txt

Configuration

- Ensure reservations.log and restaurant_conversations.log are accessible and writable.
- Adjust parameters in app.py to configure phone numbers, conversation flow, and system settings.

Usage

Start the AI call agent using:

   python app.py

- The application will listen for incoming calls.
- AI will handle reservations and inquiries based on voice input.
- Data will be logged automatically.

Logs

- reservations.log: Tracks reservation data with timestamps.
- restaurant_conversations.log: Captures conversations for quality assurance and analysis.

Enhancements

Take your AI agent to the next level:
- Integrate with CRM Systems: Connect to platforms like HubSpot, Zoho, or custom restaurant management tools.
- Advanced AI Models: Incorporate Whisper AI or GPT models for enhanced conversational capabilities.
- Multilingual Support: Expand services with multilingual voice interaction.

Contributing

We welcome contributions!
- Submit issues or enhancement requests via GitHub Issues.
- Create pull requests for bug fixes and improvements.

License

This project is licensed under the MIT License. See the LICENSE file for details.

Happy automating!
