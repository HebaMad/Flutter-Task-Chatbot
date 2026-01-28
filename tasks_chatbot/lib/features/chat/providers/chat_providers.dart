import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tasks_chatbot/features/chat/data/chat_models.dart';
import 'package:tasks_chatbot/features/tasks/providers/task_providers.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

final chatProvider = StateNotifierProvider<ChatNotifier, List<ChatMessage>>((ref) {
  return ChatNotifier(ref);
});

class ChatNotifier extends StateNotifier<List<ChatMessage>> {
  final Ref ref;
  ChatNotifier(this.ref) : super([]);

  Future<void> sendMessage(String text) async {
    final userMsg = ChatMessage(text: text, isUser: true);
    state = [...state, userMsg];

    try {
      final repo = ref.read(taskRepositoryProvider);
      final response = await http.post(
        Uri.parse('${repo.baseUrl}/v1/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'userId': repo.userId,
          'message': text,
          'timezone': 'Africa/Cairo',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));
        final botReply = data['reply'] ?? 'No reply from server';
        final candidatesRaw = data['candidates'] as List?;
        
        final botMsg = ChatMessage(
          text: botReply,
          isUser: false,
          candidates: candidatesRaw?.map((e) => e as Map<String, dynamic>).toList(),
        );
        state = [...state, botMsg];

        // If an action was performed, refresh the tasks
        final actions = data['actions'] as List?;
        if (actions != null && actions.any((a) => a['type'] != 'clarify')) {
          ref.read(tasksProvider.notifier).loadTasks();
        }
      } else {
        state = [...state, ChatMessage(text: 'Error: ${response.statusCode}', isUser: false)];
      }
    } catch (e) {
      state = [...state, ChatMessage(text: 'Error: $e', isUser: false)];
    }
  }

  void selectCandidate(Map<String, dynamic> candidate) {
    // Send the choice back as a message or handle directly (English)
    sendMessage('Select ${candidate['title']}');
  }
}
