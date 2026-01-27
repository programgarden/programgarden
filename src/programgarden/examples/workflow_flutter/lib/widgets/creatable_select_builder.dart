import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'creatable_select_builder.g.dart';

/// 생성 가능한 선택 드롭다운 빌더
///
/// 파일/DB 등 리소스를 선택하고, 새로 생성하거나 삭제할 수 있는 드롭다운
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_creatable_select",
///   "args": {
///     "decoration": {"labelText": "데이터베이스"},
///     "source": "sqlite",
///     "fileExtension": ".db",
///     "createLabel": "새 DB 생성",
///     "deletable": true
///   }
/// }
/// ```
@jsonWidget
abstract class _CreatableSelectBuilder extends JsonWidgetBuilder {
  const _CreatableSelectBuilder({required super.args});

  @override
  _CreatableSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _CreatableSelect extends StatefulWidget {
  const _CreatableSelect({
    this.decoration,
    this.source,
    this.fileExtension,
    this.createLabel,
    this.deletable,
    this.fieldKey,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final dynamic decoration;
  final String? source;
  final String? fileExtension;
  final String? createLabel;
  final dynamic deletable;
  final String? fieldKey;
  final JsonWidgetData data;

  @override
  State<_CreatableSelect> createState() => _CreatableSelectState();
}

class _CreatableSelectState extends State<_CreatableSelect> {
  String? _selectedValue;
  List<String> _items = [];
  bool _isLoading = false;

  bool get _isDeletable {
    if (widget.deletable is bool) return widget.deletable as bool;
    return false;
  }

  @override
  void initState() {
    super.initState();
    _loadItems();
  }

  Future<void> _loadItems() async {
    if (widget.source == null) return;

    setState(() => _isLoading = true);
    try {
      final response = await http.get(
        Uri.parse('http://localhost:8766/api/files/${widget.source}'),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final files = data['files'] as List? ?? [];
        setState(() {
          _items = files.map((f) => f.toString()).toList();
        });
      }
    } catch (e) {
      debugPrint('[CreatableSelect] Failed to load items: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _deleteItem(String name) async {
    if (widget.source == null) return;

    try {
      final response = await http.delete(
        Uri.parse(
          'http://localhost:8766/api/files/${widget.source}/$name',
        ),
      );
      if (response.statusCode == 200) {
        if (_selectedValue == name) {
          _selectedValue = null;
          if (widget.fieldKey != null) {
            widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, null);
          }
        }
        _loadItems();
      }
    } catch (e) {
      debugPrint('[CreatableSelect] Failed to delete item: $e');
    }
  }

  void _showCreateDialog() {
    final controller = TextEditingController();
    final ext = widget.fileExtension ?? '';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(widget.createLabel ?? '새로 만들기'),
        content: TextField(
          controller: controller,
          decoration: InputDecoration(
            labelText: '이름',
            hintText: '입력하세요',
            suffixText: ext,
            border: const OutlineInputBorder(),
          ),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () {
              final name = controller.text.trim();
              if (name.isNotEmpty) {
                final fullName = name.endsWith(ext) ? name : '$name$ext';
                setState(() {
                  if (!_items.contains(fullName)) {
                    _items.add(fullName);
                  }
                  _selectedValue = fullName;
                });
                if (widget.fieldKey != null) {
                  widget.data.jsonWidgetRegistry
                      .setValue(widget.fieldKey!, fullName);
                }
                Navigator.of(ctx).pop();
              }
            },
            child: const Text('생성'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? '선택';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: DropdownButtonFormField<String>(
            initialValue: _selectedValue,
            decoration: InputDecoration(
              labelText: labelText,
              border: const OutlineInputBorder(),
              suffixIcon: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: Padding(
                        padding: EdgeInsets.all(12),
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : null,
            ),
            items: [
              const DropdownMenuItem(
                value: '',
                child: Text(
                  '(선택하세요)',
                  style: TextStyle(color: Colors.grey),
                ),
              ),
              ..._items.map(
                (item) => DropdownMenuItem(
                  value: item,
                  child: Row(
                    children: [
                      Expanded(child: Text(item)),
                      if (_isDeletable)
                        IconButton(
                          icon: Icon(Icons.close, size: 16, color: Colors.red[400]),
                          onPressed: () => _deleteItem(item),
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                          tooltip: '삭제',
                        ),
                    ],
                  ),
                ),
              ),
            ],
            onChanged: (value) {
              setState(() {
                _selectedValue = value;
              });
              if (widget.fieldKey != null && value != null) {
                widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, value);
              }
            },
          ),
        ),
        const SizedBox(width: 8),
        IconButton(
          icon: const Icon(Icons.add_circle_outline),
          tooltip: widget.createLabel ?? '새로 만들기',
          onPressed: _showCreateDialog,
        ),
        IconButton(
          icon: const Icon(Icons.refresh),
          tooltip: '새로고침',
          onPressed: _loadItems,
        ),
      ],
    );
  }
}
