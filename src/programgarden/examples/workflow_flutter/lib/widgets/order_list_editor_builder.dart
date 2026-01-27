import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'order_list_editor_builder.g.dart';

/// 주문 목록 에디터 빌더
///
/// NewOrderNode의 orders 필드를 위한 주문 도메인 특화 테이블
/// 4컬럼(symbol, exchange, quantity, price) DataTable
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_order_list_editor",
///   "args": {
///     "decoration": {"labelText": "주문 목록"},
///     "objectSchema": [
///       {"name": "symbol", "type": "STRING"},
///       {"name": "exchange", "type": "ENUM", "enum_values": ["NASD", "NYSE", "AMEX"]},
///       {"name": "quantity", "type": "INTEGER"},
///       {"name": "price", "type": "NUMBER"}
///     ],
///     "exampleBinding": "{{ nodes.condition.orders }}",
///     "bindableSources": ["condition.orders", "screener.symbols"]
///   }
/// }
/// ```
@jsonWidget
abstract class _OrderListEditorBuilder extends JsonWidgetBuilder {
  const _OrderListEditorBuilder({required super.args});

  @override
  _OrderListEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _OrderListEditor extends StatefulWidget {
  const _OrderListEditor({
    this.decoration,
    this.objectSchema,
    this.exampleBinding,
    this.bindableSources,
    this.fieldKey,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final dynamic decoration;
  final List<dynamic>? objectSchema;
  final String? exampleBinding;
  final List<dynamic>? bindableSources;
  final String? fieldKey;
  final JsonWidgetData data;

  @override
  State<_OrderListEditor> createState() => _OrderListEditorState();
}

class _OrderListEditorState extends State<_OrderListEditor> {
  final List<Map<String, dynamic>> _orders = [];
  late List<_OrderColSchema> _columns;

  @override
  void initState() {
    super.initState();
    _columns = _parseColumns();
  }

  List<_OrderColSchema> _parseColumns() {
    final schema = widget.objectSchema;
    if (schema == null || schema.isEmpty) {
      // 기본 주문 컬럼
      return [
        _OrderColSchema(name: 'symbol', displayName: '종목코드', type: 'STRING'),
        _OrderColSchema(
          name: 'exchange',
          displayName: '거래소',
          type: 'ENUM',
          enumValues: ['NASD', 'NYSE', 'AMEX'],
        ),
        _OrderColSchema(name: 'quantity', displayName: '수량', type: 'INTEGER'),
        _OrderColSchema(name: 'price', displayName: '가격', type: 'NUMBER'),
      ];
    }

    return schema.map((col) {
      if (col is Map) {
        final map = Map<String, dynamic>.from(col);
        return _OrderColSchema(
          name: map['name'] as String? ?? '',
          displayName: (map['display_name'] as String?) ??
              (map['name'] as String? ?? '').replaceAll('_', ' '),
          type: (map['type'] as String? ?? 'STRING').toUpperCase(),
          enumValues: map['enum_values'] is List
              ? List<String>.from(map['enum_values'])
              : null,
          enumLabels: map['enum_labels'] is Map
              ? Map<String, String>.from(map['enum_labels'])
              : null,
        );
      }
      return _OrderColSchema(name: '', displayName: '', type: 'STRING');
    }).toList();
  }

  void _addOrder() {
    setState(() {
      final order = <String, dynamic>{};
      for (final col in _columns) {
        if (col.type == 'ENUM' && col.enumValues != null && col.enumValues!.isNotEmpty) {
          order[col.name] = col.enumValues!.first;
        } else if (col.type == 'INTEGER' || col.type == 'NUMBER') {
          order[col.name] = '';
        } else {
          order[col.name] = '';
        }
      }
      _orders.add(order);
    });
    _notifyChanged();
  }

  void _removeOrder(int index) {
    setState(() {
      _orders.removeAt(index);
    });
    _notifyChanged();
  }

  void _updateCell(int rowIndex, String colName, dynamic value) {
    setState(() {
      _orders[rowIndex][colName] = value;
    });
    _notifyChanged();
  }

  void _notifyChanged() {
    if (widget.fieldKey != null) {
      widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, _orders);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? '주문 목록';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // 헤더
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
            TextButton.icon(
              onPressed: _addOrder,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('주문 추가'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        if (_orders.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '주문을 추가하세요',
                style: TextStyle(color: Colors.grey[600]),
              ),
            ),
          )
        else
          Container(
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
                columnSpacing: 12,
                horizontalMargin: 12,
                columns: [
                  ..._columns.map(
                    (col) => DataColumn(label: Text(col.displayName)),
                  ),
                  const DataColumn(label: Text('')),
                ],
                rows: List.generate(_orders.length, (index) {
                  final order = _orders[index];
                  return DataRow(
                    cells: [
                      ..._columns.map(
                        (col) => DataCell(
                          _buildCellWidget(col, order, index),
                        ),
                      ),
                      DataCell(
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 20),
                          color: Colors.red[400],
                          onPressed: () => _removeOrder(index),
                          tooltip: '삭제',
                        ),
                      ),
                    ],
                  );
                }),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildCellWidget(
    _OrderColSchema col,
    Map<String, dynamic> order,
    int rowIndex,
  ) {
    switch (col.type) {
      case 'ENUM':
        final currentValue = order[col.name]?.toString();
        final items = col.enumValues ?? [];
        return SizedBox(
          width: 110,
          child: DropdownButton<String>(
            value: items.contains(currentValue) ? currentValue : (items.isNotEmpty ? items.first : null),
            underline: const SizedBox.shrink(),
            isDense: true,
            isExpanded: true,
            items: items
                .map(
                  (v) => DropdownMenuItem(
                    value: v,
                    child: Text(
                      col.enumLabels?[v] ?? v,
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                )
                .toList(),
            onChanged: (value) {
              if (value != null) {
                _updateCell(rowIndex, col.name, value);
              }
            },
          ),
        );

      case 'INTEGER':
      case 'NUMBER':
        return SizedBox(
          width: 100,
          child: TextFormField(
            initialValue: order[col.name]?.toString() ?? '',
            decoration: InputDecoration(
              hintText: col.displayName,
              border: InputBorder.none,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(vertical: 8),
            ),
            keyboardType: TextInputType.number,
            onChanged: (value) {
              _updateCell(rowIndex, col.name, value);
            },
          ),
        );

      default: // STRING
        return SizedBox(
          width: 120,
          child: TextFormField(
            initialValue: order[col.name]?.toString() ?? '',
            decoration: InputDecoration(
              hintText: col.displayName,
              border: InputBorder.none,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(vertical: 8),
            ),
            onChanged: (value) {
              _updateCell(rowIndex, col.name, value.toUpperCase());
            },
          ),
        );
    }
  }
}

/// 주문 컬럼 스키마
class _OrderColSchema {
  const _OrderColSchema({
    required this.name,
    required this.displayName,
    required this.type,
    this.enumValues,
    this.enumLabels,
  });

  final String name;
  final String displayName;
  final String type;
  final List<String>? enumValues;
  final Map<String, String>? enumLabels;
}
