import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'plugin_select_builder.g.dart';

/// Plugin 선택 드롭다운 빌더
@jsonWidget
abstract class _PluginSelectBuilder extends JsonWidgetBuilder {
  const _PluginSelectBuilder({required super.args});

  @override
  _PluginSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _PluginSelect extends StatelessWidget {
  const _PluginSelect({this.decoration, this.pluginCategory, super.key});

  final dynamic decoration;
  final String? pluginCategory;

  @override
  Widget build(BuildContext context) {
    final dec = decoration is Map
        ? Map<String, dynamic>.from(decoration)
        : <String, dynamic>{};

    return DropdownButtonFormField<String>(
      decoration: InputDecoration(
        labelText: dec['labelText'] as String? ?? 'Plugin',
        helperText: dec['helperText'] as String?,
        border: const OutlineInputBorder(),
      ),
      items: const [
        DropdownMenuItem(
          value: '',
          child: Text('(플러그인 선택)', style: TextStyle(color: Colors.grey)),
        ),
      ],
      onChanged: (value) {},
      hint: const Text('플러그인 선택...'),
    );
  }
}
