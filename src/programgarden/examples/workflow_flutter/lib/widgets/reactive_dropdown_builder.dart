import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'reactive_dropdown_builder.g.dart';

/// Dropdown 빌더 - dropdown_button_form_field 타입 오버라이드
///
/// 값 변경 시 registry.setValue()를 호출하여
/// json_dynamic_widget 내장 conditional 위젯이 조건부 렌더링을 수행합니다.
@jsonWidget
abstract class _DropdownButtonFormFieldBuilder extends JsonWidgetBuilder {
  const _DropdownButtonFormFieldBuilder({required super.args});

  @override
  _DropdownButtonFormField buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _DropdownButtonFormField extends StatefulWidget {
  const _DropdownButtonFormField({
    super.key,
    this.decoration,
    required this.items,
    this.value,
    this.validators,
    this.fieldKey,
    this.itemLabels,
    this.helperText,
    @JsonBuildArg() required this.data,
  });

  final dynamic decoration;
  final List<dynamic> items;
  final dynamic value;
  final dynamic validators;
  final String? fieldKey;
  final dynamic itemLabels;
  final String? helperText;
  final JsonWidgetData data;

  @override
  State<_DropdownButtonFormField> createState() =>
      _DropdownButtonFormFieldState();
}

class _DropdownButtonFormFieldState extends State<_DropdownButtonFormField> {
  late dynamic _selectedValue;

  @override
  void initState() {
    super.initState();
    debugPrint(
      '🔥🔥🔥 [DropdownBuilder] CUSTOM WIDGET CREATED! fieldKey=${widget.fieldKey}',
    );
    _selectedValue = widget.value;

    // 초기값을 registry에 저장 (conditional 위젯이 이 값을 감시)
    if (widget.fieldKey != null && _selectedValue != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        debugPrint(
          '🔥 [DropdownBuilder] initState: setValue(${widget.fieldKey}, $_selectedValue)',
        );
        widget.data.jsonWidgetRegistry.setValue(
          widget.fieldKey!,
          _selectedValue,
        );
      });
    }
  }

  String _getLabel(dynamic item) {
    if (item is Map) {
      return item['label']?.toString() ?? item['value']?.toString() ?? '';
    }
    final value = item.toString();
    final labels = widget.itemLabels;
    if (labels is Map && labels.containsKey(value)) {
      return labels[value].toString();
    }
    return value;
  }

  dynamic _getValue(dynamic item) {
    if (item is Map) {
      return item['value'];
    }
    return item;
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration;
    final labelText = dec is Map ? (dec['labelText']?.toString() ?? '') : '';

    final dropdownItems = widget.items.map((item) {
      final value = _getValue(item);
      final label = _getLabel(item);
      return DropdownMenuItem<dynamic>(value: value, child: Text(label));
    }).toList();

    final isRequired =
        widget.validators?.toString().contains('required') ?? false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        DropdownButtonFormField<dynamic>(
          decoration: InputDecoration(
            labelText: labelText,
            border: const OutlineInputBorder(),
          ),
          initialValue: _selectedValue,
          items: dropdownItems,
          onChanged: (newValue) {
            setState(() {
              _selectedValue = newValue;
            });
            // registry에 값 저장 → conditional 위젯이 이 변경을 감지
            if (widget.fieldKey != null && newValue != null) {
              debugPrint(
                '🔥 [DropdownBuilder] onChanged: setValue(${widget.fieldKey}, $newValue)',
              );
              widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, newValue);
            }
          },
          validator: isRequired
              ? (value) => value == null ? '필수 항목입니다' : null
              : null,
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
