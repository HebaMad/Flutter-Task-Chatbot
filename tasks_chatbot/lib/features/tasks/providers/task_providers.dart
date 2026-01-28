import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:tasks_chatbot/features/tasks/data/task_model.dart';
import 'package:tasks_chatbot/features/tasks/data/task_repository.dart';

final taskRepositoryProvider = Provider<TaskRepository>((ref) {
  // In a real app, baseUrl and userId would come from config/auth
  return TaskRepository(
    baseUrl: 'http://localhost:8000', 
    userId: 'u123',
  );
});

final tasksProvider = StateNotifierProvider<TasksNotifier, AsyncValue<List<Task>>>((ref) {
  return TasksNotifier(ref.watch(taskRepositoryProvider));
});

class TasksNotifier extends StateNotifier<AsyncValue<List<Task>>> {
  final TaskRepository _repository;

  TasksNotifier(this._repository) : super(const AsyncValue.loading()) {
    loadTasks();
  }

  Future<void> loadTasks() async {
    state = const AsyncValue.loading();
    try {
      final tasks = await _repository.getTasks();
      state = AsyncValue.data(tasks);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> addTask(String title) async {
    try {
      await _repository.createTask(title);
      await loadTasks();
    } catch (e) {
      // handle error
    }
  }

  Future<void> toggleTask(Task task) async {
    try {
      await _repository.updateTask(task.id, completed: !task.completed);
      await loadTasks();
    } catch (e) {
      // handle error
    }
  }

  Future<void> updateTaskDetails(String id, {String? title, String? description, String? priority, bool? completed}) async {
    try {
      await _repository.updateTask(id, title: title, description: description, priority: priority, completed: completed);
      await loadTasks();
    } catch (e) {
      // handle error
    }
  }

  Future<void> deleteTask(String id) async {
    try {
      await _repository.deleteTask(id);
      await loadTasks();
    } catch (e) {
      // handle error
    }
  }
}
