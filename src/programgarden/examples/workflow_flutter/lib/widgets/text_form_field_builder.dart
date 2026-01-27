import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'text_form_field_builder.g.dart';

/// TextFormField 빌더 - text_form_field 타입 오버라이드
///
/// 네이티브 json_dynamic_widget의 text_form_field는 args.helperText를 지원하지 않으므로,
/// FIXED_ONLY 필드의 description을 커스텀 렌더링하기 위해 오버라이드합니다.
///
/// JSON 스키마 예시:
/// ```json
/// {
///   "type": "text_form_field",
///   "args": {
///     "decoration": {"labelText": "Interval Sec", "hintText": "5.0"},
///     "keyboardType": "number",
///     "initialValue": "5.0",
///     "helperText": "최소 실행 간격 (초)"
///   }
/// }
/// ```
@jsonWidget
abstract class _TextFormFieldOverrideBuilder extends JsonWidgetBuilder {
  const _TextFormFieldOverrideBuilder({required super.args});

  @override
  _TextFormFieldOverride buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _TextFormFieldOverride extends StatefulWidget {
  const _TextFormFieldOverride({
    super.key,
    this.decoration,
    this.initialValue,
    this.maxLines,
    this.keyboardType,
    this.fieldKey,
    this.helperText,
    this.validators,
    @JsonBuildArg() required this.data,
  });

  final dynamic decoration;
  final String? initialValue;
  final dynamic maxLines;
  final String? keyboardType;
  final String? fieldKey;
  final String? helperText;
  final dynamic validators;
  final JsonWidgetData data;

  @override
  State<_TextFormFieldOverride> createState() => _TextFormFieldOverrideState();
}

class _TextFormFieldOverrideState extends State<_TextFormFieldOverride> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue ?? '');

    if (widget.fieldKey != null && widget.initialValue != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.data.jsonWidgetRegistry.setValue(
          widget.fieldKey!,
          widget.initialValue,
        );
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  TextInputType? _parseKeyboardType(String? type) {
    if (type == null) return null;
    switch (type) {
      case 'number':
        return TextInputType.number;
      case 'email':
        return TextInputType.emailAddress;
      case 'url':
        return TextInputType.url;
      case 'phone':
        return TextInputType.phone;
      case 'multiline':
        return TextInputType.multiline;
      default:
        return TextInputType.text;
    }
  }

  int? _parseMaxLines() {
    final ml = widget.maxLines;
    if (ml is int) return ml;
    if (ml is String) return int.tryParse(ml);
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration;
    final labelText = dec is Map ? (dec['labelText']?.toString() ?? '') : '';
    final hintText = dec is Map ? dec['hintText']?.toString() : null;

    final maxLines = _parseMaxLines();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        TextFormField(
          controller: _controller,
          decoration: InputDecoration(
            labelText: labelText,
            hintText: hintText,
            border: const OutlineInputBorder(),
          ),
          keyboardType: _parseKeyboardType(widget.keyboardType),
          maxLines: maxLines ?? 1,
          onChanged: (value) {
            if (widget.fieldKey != null) {
              widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, value);
            }
          },
        ),
        if (widget.helperText != null && widget.helperText!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: 12, top: 4),
            child: Text(
              widget.helperText!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).hintColor,
              ),
            ),
          ),
      ],
    );
  }
}
