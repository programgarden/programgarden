import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'code_editor_builder.g.dart';

/// 코드 에디터 빌더
///
/// SQL 등 코드 입력을 위한 모노스페이스 멀티라인 텍스트 에디터
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_code_editor",
///   "args": {
///     "decoration": {"labelText": "SQL 쿼리"},
///     "language": "sql"
///   }
/// }
/// ```
@jsonWidget
abstract class _CodeEditorBuilder extends JsonWidgetBuilder {
  const _CodeEditorBuilder({required super.args});

  @override
  _CodeEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _CodeEditor extends StatefulWidget {
  const _CodeEditor({
    this.decoration,
    this.language,
    this.fieldKey,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final dynamic decoration;
  final String? language;
  final String? fieldKey;
  final JsonWidgetData data;

  @override
  State<_CodeEditor> createState() => _CodeEditorState();
}

class _CodeEditorState extends State<_CodeEditor> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? 'Code';
    final hintText = dec['hintText'] as String?;
    final lang = widget.language ?? 'sql';

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade600),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // 헤더: 라벨 + 언어 표시
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF2D2D2D),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(7)),
            ),
            child: Row(
              children: [
                Text(
                  labelText,
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade700,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    lang.toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white60,
                      fontSize: 10,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ],
            ),
          ),
          // 코드 입력 영역
          Padding(
            padding: const EdgeInsets.all(8),
            child: TextFormField(
              controller: _controller,
              maxLines: 12,
              minLines: 5,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 13,
                color: Color(0xFFD4D4D4),
                height: 1.5,
              ),
              decoration: InputDecoration(
                hintText: hintText ?? _getHintForLanguage(lang),
                hintStyle: TextStyle(
                  color: Colors.grey.shade600,
                  fontFamily: 'monospace',
                  fontSize: 13,
                ),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.all(8),
                isDense: true,
              ),
              onChanged: (value) {
                if (widget.fieldKey != null) {
                  widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, value);
                }
              },
            ),
          ),
        ],
      ),
    );
  }

  String _getHintForLanguage(String lang) {
    switch (lang) {
      case 'sql':
        return 'SELECT * FROM table WHERE ...';
      case 'python':
        return '# Python code here...';
      case 'json':
        return '{\n  "key": "value"\n}';
      default:
        return 'Enter code here...';
    }
  }
}
