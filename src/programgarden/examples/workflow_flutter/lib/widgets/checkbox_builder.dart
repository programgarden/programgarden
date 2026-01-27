import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'checkbox_builder.g.dart';

/// Checkbox 빌더
///
/// JSON 스키마 예시:
/// ```json
/// {
///   "type": "checkbox",
///   "args": {
///     "value": true,
///     "fieldKey": "stay_connected"
///   }
/// }
/// ```
///
/// FIXED_ONLY 모드: args.helperText로 직접 렌더링
/// BOTH/EXPRESSION_ONLY 모드: custom_expression_toggle의 fixedHelperText로 관리
@jsonWidget
abstract class _CheckboxBuilder extends JsonWidgetBuilder {
  const _CheckboxBuilder({required super.args});

  @override
  _CheckboxWidget buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _CheckboxWidget extends StatefulWidget {
  const _CheckboxWidget({
    super.key,
    this.value,
    this.fieldKey,
    this.labelText,
    this.helperText,
    @JsonBuildArg() required this.data,
  });

  final bool? value;
  final String? fieldKey;
  final String? labelText;
  final String? helperText;
  final JsonWidgetData data;

  @override
  State<_CheckboxWidget> createState() => _CheckboxWidgetState();
}

class _CheckboxWidgetState extends State<_CheckboxWidget> {
  late bool _checked;

  @override
  void initState() {
    super.initState();
    _checked = widget.value ?? false;

    // 초기값을 registry에 저장
    if (widget.fieldKey != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, _checked);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Checkbox(
              value: _checked,
              onChanged: (newValue) {
                setState(() {
                  _checked = newValue ?? false;
                });
                // registry에 값 저장
                if (widget.fieldKey != null) {
                  widget.data.jsonWidgetRegistry.setValue(
                    widget.fieldKey!,
                    _checked,
                  );
                }
              },
            ),
            if (widget.labelText != null)
              Expanded(
                child: GestureDetector(
                  onTap: () {
                    setState(() {
                      _checked = !_checked;
                    });
                    if (widget.fieldKey != null) {
                      widget.data.jsonWidgetRegistry.setValue(
                        widget.fieldKey!,
                        _checked,
                      );
                    }
                  },
                  child: Text(
                    widget.labelText!,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ),
          ],
        ),
        if (widget.helperText != null && widget.helperText!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(left: 8, top: 4),
            child: Text(
              widget.helperText!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.hintColor,
              ),
            ),
          ),
      ],
    );
  }
}
