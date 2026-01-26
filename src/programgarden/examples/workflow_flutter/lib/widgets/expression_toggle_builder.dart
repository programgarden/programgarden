import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'expression_toggle_builder.g.dart';

/// Fixed/Expression 토글 빌더
///
/// BOTH 모드 필드에서 고정값 입력과 바인딩 표현식 입력을 토글로 전환할 수 있게 합니다.
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_expression_toggle",
///   "args": {
///     "fieldKey": "symbols",
///     "label": "종목 목록",
///     "fixedHelperText": "고정값 입력 시 설명",
///     "expressionHelperText": "바인딩 입력 시 설명",
///     "defaultMode": "fixed",
///     "lockedMode": null,
///     "expressionHint": "{{ nodes.watchlist.symbols }}",
///     "fixedWidget": { ... },
///     "expressionWidget": { ... }
///   }
/// }
/// ```
@jsonWidget
abstract class _ExpressionToggleBuilder extends JsonWidgetBuilder {
  const _ExpressionToggleBuilder({required super.args});

  @override
  _ExpressionToggle buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _ExpressionToggle extends StatefulWidget {
  const _ExpressionToggle({
    required this.fieldKey,
    this.label,
    this.fixedHelperText,
    this.expressionHelperText,
    this.defaultMode,
    this.lockedMode,
    this.expressionHint,
    this.fixedWidget,
    this.expressionWidget,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final String fieldKey;
  final String? label;
  final String? fixedHelperText;
  final String? expressionHelperText;
  final String? defaultMode;
  final String? lockedMode; // "fixed", "expression", or null (both allowed)
  final String? expressionHint;
  final dynamic fixedWidget;
  final dynamic expressionWidget;
  final JsonWidgetData data;

  @override
  State<_ExpressionToggle> createState() => _ExpressionToggleState();
}

class _ExpressionToggleState extends State<_ExpressionToggle> {
  late bool _isExpression;

  @override
  void initState() {
    super.initState();
    // lockedMode가 있으면 해당 모드로 고정, 없으면 defaultMode 사용
    if (widget.lockedMode != null) {
      _isExpression = widget.lockedMode == 'expression';
    } else {
      _isExpression = widget.defaultMode == 'expression';
    }
  }

  @override
  Widget build(BuildContext context) {
    // json_dynamic_widget 레지스트리 가져오기
    final registry = widget.data.jsonWidgetRegistry;

    // lockedMode가 있으면 토글 비활성화
    final isLocked = widget.lockedMode != null;

    // 현재 모드에 따른 helperText 선택 및 i18n 처리
    final rawHelperText = _isExpression
        ? widget.expressionHelperText
        : widget.fixedHelperText;
    final currentHelperText = _translateI18n(rawHelperText);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // 라벨 + 토글 버튼 Row
        Row(
          children: [
            // 라벨 (fixedWidget 내부에서 표시하므로 여기서는 제거)
            const Spacer(),
            // Fixed/Expression 토글 버튼
            _buildToggleButton(isLocked),
          ],
        ),
        const SizedBox(height: 8),
        // 선택에 따른 위젯 표시
        if (_isExpression)
          _buildExpressionWidget(registry)
        else
          _buildFixedWidget(registry),
        // 헬퍼 텍스트 (모드에 따라 다른 텍스트 표시)
        if (currentHelperText != null && currentHelperText.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              currentHelperText,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).hintColor,
              ),
            ),
          ),
      ],
    );
  }

  /// i18n 키를 번역 (서버에서 번역되지 않은 경우 클라이언트에서 처리)
  /// "i18n:fields.RealAccountNode.product_type" → 빈 문자열 또는 기본 메시지
  String? _translateI18n(String? text) {
    if (text == null) return null;
    if (text.startsWith('i18n:')) {
      // i18n 키는 서버에서 번역되어야 하지만, 번역되지 않은 경우 숨김
      // TODO: 클라이언트 측 번역 로직 추가 가능
      debugPrint('[ExpressionToggle] Untranslated i18n key: $text');
      return null; // 번역되지 않은 키는 표시하지 않음
    }
    return text;
  }

  /// 토글 버튼 빌드 (lockedMode 시 선택된 상태로 비활성화 표시)
  Widget _buildToggleButton(bool isLocked) {
    final theme = Theme.of(context);
    final selectedColor = theme.colorScheme.primary;
    final unselectedColor = theme.colorScheme.surfaceContainerHighest;

    return Opacity(
      opacity: isLocked ? 0.7 : 1.0,
      child: SegmentedButton<bool>(
        segments: [
          ButtonSegment<bool>(
            value: false,
            label: Text(
              'Fixed',
              style: TextStyle(
                fontWeight: !_isExpression
                    ? FontWeight.bold
                    : FontWeight.normal,
                color: !_isExpression ? selectedColor : null,
              ),
            ),
            icon: Icon(
              Icons.text_fields,
              size: 16,
              color: !_isExpression ? selectedColor : null,
            ),
          ),
          ButtonSegment<bool>(
            value: true,
            label: Text(
              'fx',
              style: TextStyle(
                fontWeight: _isExpression ? FontWeight.bold : FontWeight.normal,
                color: _isExpression ? selectedColor : null,
              ),
            ),
            icon: Icon(
              Icons.functions,
              size: 16,
              color: _isExpression ? selectedColor : null,
            ),
          ),
        ],
        selected: {_isExpression},
        onSelectionChanged: isLocked
            ? null
            : (selection) {
                setState(() {
                  _isExpression = selection.first;
                });
              },
        showSelectedIcon: false,
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      ),
    );
  }

  Widget _buildFixedWidget(JsonWidgetRegistry registry) {
    if (widget.fixedWidget == null) {
      debugPrint(
        '[ExpressionToggle] fixedWidget is null for ${widget.fieldKey}',
      );
      return const SizedBox.shrink();
    }

    try {
      debugPrint(
        '[ExpressionToggle] Building fixedWidget for ${widget.fieldKey}: ${widget.fixedWidget}',
      );

      // fixedWidget에 fieldKey를 자동으로 주입 (conditional이 동작하도록)
      final widgetJson = _injectFieldKey(widget.fixedWidget, widget.fieldKey);

      final widgetData = JsonWidgetData.fromDynamic(
        widgetJson,
        registry: registry,
      );
      return widgetData.build(context: context, registry: registry);
    } catch (e, stackTrace) {
      debugPrint(
        '[ExpressionToggle] Error building fixedWidget for ${widget.fieldKey}: $e',
      );
      debugPrint('$stackTrace');
      return Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.red),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          'Error: $e',
          style: const TextStyle(color: Colors.red, fontSize: 12),
        ),
      );
    }
  }

  /// fixedWidget JSON에 fieldKey를 주입
  /// dropdown, text_form_field 등에서 registry.setValue를 호출하도록 함
  dynamic _injectFieldKey(dynamic widgetJson, String fieldKey) {
    if (widgetJson == null) return null;
    if (widgetJson is! Map) return widgetJson;

    final result = Map<String, dynamic>.from(widgetJson);
    final args = result['args'];

    if (args is Map) {
      final newArgs = Map<String, dynamic>.from(args);
      // fieldKey가 없으면 추가
      if (!newArgs.containsKey('fieldKey')) {
        newArgs['fieldKey'] = fieldKey;
      }
      result['args'] = newArgs;
    } else {
      result['args'] = {'fieldKey': fieldKey};
    }

    // 최상위에도 field_key_of_pydantic 추가 (일부 위젯에서 사용)
    if (!result.containsKey('field_key_of_pydantic')) {
      result['field_key_of_pydantic'] = fieldKey;
    }

    debugPrint(
      '[ExpressionToggle] Injected fieldKey=$fieldKey into fixedWidget',
    );
    return result;
  }

  Widget _buildExpressionWidget(JsonWidgetRegistry registry) {
    if (widget.expressionWidget == null) {
      debugPrint(
        '[ExpressionToggle] expressionWidget is null for ${widget.fieldKey}',
      );
      // expressionWidget이 없으면 기본 텍스트 필드
      return TextFormField(
        decoration: InputDecoration(
          hintText: widget.expressionHint ?? '{{ nodes.xxx.yyy }}',
          border: const OutlineInputBorder(),
        ),
        onChanged: (value) {
          // 레지스트리에 값 저장
          registry.setValue(widget.fieldKey, value);
        },
      );
    }

    try {
      debugPrint(
        '[ExpressionToggle] Building expressionWidget for ${widget.fieldKey}: ${widget.expressionWidget}',
      );
      final widgetData = JsonWidgetData.fromDynamic(
        widget.expressionWidget,
        registry: registry,
      );
      return widgetData.build(context: context, registry: registry);
    } catch (e, stackTrace) {
      debugPrint(
        '[ExpressionToggle] Error building expressionWidget for ${widget.fieldKey}: $e',
      );
      debugPrint('$stackTrace');
      return Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.red),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          'Error: $e',
          style: const TextStyle(color: Colors.red, fontSize: 12),
        ),
      );
    }
  }
}
