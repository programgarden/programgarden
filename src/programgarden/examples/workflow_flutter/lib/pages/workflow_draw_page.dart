import 'package:flutter/material.dart';

class WorkflowDrawPage extends StatelessWidget {
  const WorkflowDrawPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('워크플로우 그리기'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: const Center(
        child: Text(
          '워크플로우 그리기 기능은 추후 구현 예정입니다.',
          style: TextStyle(fontSize: 16),
        ),
      ),
    );
  }
}
