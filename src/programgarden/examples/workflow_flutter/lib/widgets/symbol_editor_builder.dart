import 'dart:async';

import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'symbol_editor_builder.g.dart';

/// 종목 에디터 빌더
///
/// RealMarketDataNode의 symbols 필드를 위한 커스텀 위젯
/// - 상품유형 선택 (해외주식/해외선물)
/// - DataTable로 종목 목록 테이블
/// - Expression 토글 (Fixed/fx) 지원
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_symbol_editor",
///   "args": {
///     "decoration": {"labelText": "종목"},
///     "expressionMode": "both",
///     "objectSchema": [...],
///     "uiOptions": {
///       "exchanges": [
///         {"value": "NASDAQ", "label": "NASDAQ"},
///         {"value": "NYSE", "label": "NYSE"}
///       ]
///     }
///   }
/// }
/// ```
@jsonWidget
abstract class _SymbolEditorBuilder extends JsonWidgetBuilder {
  const _SymbolEditorBuilder({required super.args});

  @override
  _SymbolEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _SymbolEditor extends StatefulWidget {
  const _SymbolEditor({
    this.decoration,
    this.expressionMode,
    this.bindableSources,
    this.objectSchema,
    this.uiOptions,
    this.expressionHint,
    this.initialValue,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final dynamic decoration;
  final String? expressionMode;
  final List<dynamic>? bindableSources;
  final List<dynamic>? objectSchema;
  final dynamic uiOptions;  // LinkedMap 호환을 위해 dynamic 사용
  final String? expressionHint;
  final dynamic initialValue;
  final JsonWidgetData data;

  @override
  State<_SymbolEditor> createState() => _SymbolEditorState();
}

class _SymbolEditorState extends State<_SymbolEditor> {
  /// 현재 모드: Fixed(테이블) vs Expression(fx 바인딩)
  late bool _isExpression;

  /// 종목 목록 데이터 [{exchange, symbol}, ...]
  late List<Map<String, String>> _symbols;

  /// 현재 선택된 상품유형 (캐시)
  late String _currentProductType;

  /// product_type 필드명 (리스너 등록용)
  String? _productTypeFieldName;

  /// registry valueStream 구독
  StreamSubscription<dynamic>? _productTypeSubscription;

  @override
  void initState() {
    super.initState();

    // Expression 모드 초기화 (expression_only면 fx 고정)
    _isExpression = widget.expressionMode == 'expression_only';

    // 초기 종목 목록 파싱
    _symbols = _parseInitialValue();

    // 초기 상품유형 설정
    _currentProductType = _getDefaultProductType();

    // product_type 필드 변경 리스너 등록
    _setupProductTypeListener();
  }

  @override
  void dispose() {
    // 구독 해제
    _productTypeSubscription?.cancel();
    super.dispose();
  }

  /// product_type 필드 변경 리스너 설정
  void _setupProductTypeListener() {
    final uiOptions = _safeUiOptions;
    if (uiOptions == null) return;

    _productTypeFieldName = uiOptions['product_type_field'] as String?;
    if (_productTypeFieldName != null) {
      final registry = widget.data.jsonWidgetRegistry;

      // 초기값 설정
      final initialValue = registry.getValue(_productTypeFieldName!);
      if (initialValue != null && initialValue is String) {
        _currentProductType = initialValue;
      }

      // valueStream 구독하여 변경 감지
      _productTypeSubscription = registry.valueStream
          .where((event) => event.id == _productTypeFieldName)
          .listen((event) {
        final newValue = event.value;
        if (newValue is String && newValue != _currentProductType) {
          debugPrint('🔄 [SymbolEditor] product_type changed: $_currentProductType → $newValue');
          setState(() {
            _currentProductType = newValue;
            // 상품유형 변경 시 종목 테이블 초기화
            _symbols.clear();
            _notifyValueChanged();
          });
        }
      });
    }
  }

  /// uiOptions를 안전하게 Map으로 변환
  Map<String, dynamic>? get _safeUiOptions {
    if (widget.uiOptions == null) return null;
    if (widget.uiOptions is Map) {
      return Map<String, dynamic>.from(widget.uiOptions as Map);
    }
    return null;
  }

  String _getDefaultProductType() {
    final uiOptions = _safeUiOptions;
    if (uiOptions != null && uiOptions['default_product_type'] != null) {
      return uiOptions['default_product_type'] as String;
    }
    return 'overseas_stock';
  }

  List<Map<String, String>> _parseInitialValue() {
    if (widget.initialValue == null) return [];
    if (widget.initialValue is! List) return [];

    return (widget.initialValue as List).map((item) {
      if (item is Map) {
        return {
          'exchange': (item['exchange'] ?? '').toString(),
          'symbol': (item['symbol'] ?? '').toString(),
        };
      }
      return <String, String>{};
    }).toList();
  }

  /// 거래소 목록 가져오기
  List<Map<String, String>> _getExchangesForProductType() {
    final uiOptions = _safeUiOptions;
    if (uiOptions == null) return [];

    final exchanges = uiOptions['exchanges'];
    if (exchanges == null || exchanges is! List) return [];

    return exchanges.map((e) {
      if (e is Map) {
        return {
          'value': (e['value'] ?? '').toString(),
          'label': (e['label'] ?? '').toString(),
        };
      }
      return <String, String>{};
    }).toList();
  }

  void _addSymbol() {
    final exchanges = _getExchangesForProductType();
    final defaultExchange = exchanges.isNotEmpty ? exchanges.first['value']! : '';

    setState(() {
      _symbols.add({'exchange': defaultExchange, 'symbol': ''});
    });
    _notifyValueChanged();
  }

  void _removeSymbol(int index) {
    setState(() {
      _symbols.removeAt(index);
    });
    _notifyValueChanged();
  }

  void _updateSymbol(int index, String field, String value) {
    setState(() {
      _symbols[index][field] = value;
    });
    _notifyValueChanged();
  }

  void _notifyValueChanged() {
    // json_dynamic_widget 레지스트리에 값 저장
    final registry = widget.data.jsonWidgetRegistry;
    registry.setValue('symbols', _symbols);
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? '종목';
    final helperText = dec['helperText'] as String?;

    // lockedMode 결정 (expression_only → fx 고정, fixed_only → fixed 고정)
    final isLocked = widget.expressionMode == 'expression_only' ||
        widget.expressionMode == 'fixed_only';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // 헤더: 라벨 + Expression 토글
          Row(
            children: [
              Text(
                labelText,
                style: const TextStyle(
                  fontWeight: FontWeight.w500,
                  fontSize: 14,
                ),
              ),
              const Spacer(),
              // Fixed/Expression 토글 (both 모드일 때만 활성화)
              if (widget.expressionMode == 'both') _buildToggleButton(isLocked),
            ],
          ),
          const SizedBox(height: 8),

          // 선택에 따른 컨텐츠 표시
          if (_isExpression)
            _buildExpressionInput()
          else
            _buildFixedEditor(),

          // 헬퍼 텍스트
          if (helperText != null && helperText.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                helperText,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// Fixed/Expression 토글 버튼
  Widget _buildToggleButton(bool isLocked) {
    final theme = Theme.of(context);
    final selectedColor = theme.colorScheme.primary;

    return Opacity(
      opacity: isLocked ? 0.7 : 1.0,
      child: SegmentedButton<bool>(
        segments: [
          ButtonSegment<bool>(
            value: false,
            label: Text(
              'Fixed',
              style: TextStyle(
                fontWeight: !_isExpression ? FontWeight.bold : FontWeight.normal,
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
        style: const ButtonStyle(
          visualDensity: VisualDensity.compact,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
      ),
    );
  }

  /// Expression 모드: 바인딩 입력 필드
  Widget _buildExpressionInput() {
    return TextFormField(
      decoration: InputDecoration(
        hintText: widget.expressionHint ?? '{{ nodes.watchlist.symbols }}',
        border: const OutlineInputBorder(),
        prefixIcon: const Icon(Icons.functions, size: 20),
      ),
      onChanged: (value) {
        final registry = widget.data.jsonWidgetRegistry;
        registry.setValue('symbols', value);
      },
    );
  }

  /// Fixed 모드: 종목 테이블 에디터
  Widget _buildFixedEditor() {
    final exchanges = _getExchangesForProductType();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // 종목 테이블
        if (_symbols.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '종목을 추가하세요',
                style: TextStyle(color: Colors.grey[600]),
              ),
            ),
          )
        else
          _buildSymbolTable(exchanges),

        const SizedBox(height: 8),

        // 종목 추가 버튼
        TextButton.icon(
          onPressed: _addSymbol,
          icon: const Icon(Icons.add, size: 18),
          label: const Text('종목 추가'),
        ),
      ],
    );
  }

  /// 현재 거래소 값이 목록에 유효한지 확인하고, 유효하지 않으면 첫 번째 값 반환
  String? _getValidExchangeValue(String? currentValue, List<Map<String, String>> exchanges) {
    if (exchanges.isEmpty) return null;

    final validValues = exchanges.map((e) => e['value']).toSet();

    // 현재 값이 비어있거나 목록에 없으면 첫 번째 값 반환
    if (currentValue == null || currentValue.isEmpty || !validValues.contains(currentValue)) {
      return exchanges.first['value'];
    }

    return currentValue;
  }

  /// 종목 테이블 (DataTable)
  Widget _buildSymbolTable(List<Map<String, String>> exchanges) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(4),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowHeight: 40,
          dataRowMinHeight: 48,
          dataRowMaxHeight: 56,
          columnSpacing: 16,
          horizontalMargin: 12,
          columns: const [
            DataColumn(label: Text('거래소')),
            DataColumn(label: Text('종목코드')),
            DataColumn(label: Text('')),
          ],
          rows: List.generate(_symbols.length, (index) {
            final symbol = _symbols[index];
            // 현재 거래소 값이 유효한지 확인
            final validExchangeValue = _getValidExchangeValue(symbol['exchange'], exchanges);

            return DataRow(
              cells: [
                // 거래소 드롭다운
                DataCell(
                  DropdownButton<String>(
                    value: validExchangeValue,
                    underline: const SizedBox.shrink(),
                    isDense: true,
                    items: exchanges
                        .map(
                          (e) => DropdownMenuItem(
                            value: e['value'],
                            child: Text(e['label'] ?? e['value'] ?? ''),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) {
                        _updateSymbol(index, 'exchange', value);
                      }
                    },
                  ),
                ),
                // 종목코드 입력
                DataCell(
                  SizedBox(
                    width: 120,
                    child: TextFormField(
                      initialValue: symbol['symbol'],
                      decoration: const InputDecoration(
                        hintText: 'AAPL',
                        border: InputBorder.none,
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(vertical: 8),
                      ),
                      onChanged: (value) {
                        _updateSymbol(index, 'symbol', value.toUpperCase());
                      },
                    ),
                  ),
                ),
                // 삭제 버튼
                DataCell(
                  IconButton(
                    icon: const Icon(Icons.delete_outline, size: 20),
                    color: Colors.red[400],
                    onPressed: () => _removeSymbol(index),
                    tooltip: '삭제',
                  ),
                ),
              ],
            );
          }),
        ),
      ),
    );
  }
}
