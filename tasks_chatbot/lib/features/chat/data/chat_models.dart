class ChatMessage {
  final String text;
  final bool isUser;
  final List<Map<String, dynamic>>? candidates;

  ChatMessage({required this.text, required this.isUser, this.candidates});
}
