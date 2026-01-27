import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'object_array_table_builder.g.dart';

/// 객체 배열 테이블 빌더
///
/// objectSchema 기반 동적 다중 컬럼 테이블 (LogicNode.conditions)
/// 각 컬럼의 type에 따라 입력 위젯을 자동 선택:
/// - STRING -> TextFormField
/// - NUMBER/INTEGER -> TextFormField(number)
/// - ENUM -> DropdownButton
/// - BOOLEAN -> Checkbox
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_object_array_table",
///   "args": {
///     "decoration": {"labelText": "조건 목록"},
///     "objectSchema": [
///       {"name": "field", "type": "STRING"},
///       {"name": "operator", "type": "ENUM", "enum_values": ["==", "!=", ">", "<"]},
///       {"name": "value", "type": "STRING"}
///     ]
///   }
/// }
/// ```
@jsonWidget
abstract class _ObjectArrayTableBuilder extends JsonWidgetBuilder {
  const _ObjectArrayTableBuilder({required super.args});

  @override
  _ObjectArrayTable buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _ObjectArrayTable extends StatefulWidget {
  const _ObjectArrayTable({
    this.decoration,
    this.objectSchema,
    this.fieldKey,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final dynamic decoration;
  final List<dynamic>? objectSchema;
  final String? fieldKey;
  final JsonWidgetData data;

  @override
  State<_ObjectArrayTable> createState() => _ObjectArrayTableState();
}

class _ObjectArrayTableState extends State<_ObjectArrayTable> {
  final List<Map<String, dynamic>> _rows = [];
  late List<_ColSchema> _columns;

  @override
  void initState() {
    super.initState();
    _columns = _parseColumns();
  }

  List<_ColSchema> _parseColumns() {
    final schema = widget.objectSchema;
    if (schema == null || schema.isEmpty) return [];

    return schema.map((col) {
      if (col is Map) {
        final map = Map<String, dynamic>.from(col);
        return _ColSchema(
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
          defaultValue: map['default'],
          visibleWhen: map['visible_when'] is Map
              ? Map<String, dynamic>.from(map['visible_when'])
              : null,
        );
      }
      return _ColSchema(name: '', displayName: '', type: 'STRING');
    }).toList();
  }

  void _addRow() {
    setState(() {
      final row = <String, dynamic>{};
      for (final col in _columns) {
        if (col.defaultValue != null) {
          row[col.name] = col.defaultValue;
        } else if (col.type == 'ENUM' && col.enumValues != null && col.enumValues!.isNotEmpty) {
          row[col.name] = col.enumValues!.first;
        } else if (col.type == 'BOOLEAN') {
          row[col.name] = false;
        } else if (col.type == 'NUMBER' || col.type == 'INTEGER') {
          row[col.name] = '';
        } else {
          row[col.name] = '';
        }
      }
      _rows.add(row);
    });
    _notifyChanged();
  }

  void _removeRow(int index) {
    setState(() {
      _rows.removeAt(index);
    });
    _notifyChanged();
  }

  void _updateCell(int rowIndex, String colName, dynamic value) {
    setState(() {
      _rows[rowIndex][colName] = value;
    });
    _notifyChanged();
  }

  void _notifyChanged() {
    if (widget.fieldKey != null) {
      widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, _rows);
    }
  }

  /// visible_when 조건 평가: 해당 행의 다른 필드 값을 기준으로 컬럼 표시 여부 결정
  bool _isColumnVisible(_ColSchema col, Map<String, dynamic> row) {
    if (col.visibleWhen == null) return true;

    for (final entry in col.visibleWhen!.entries) {
      final fieldValue = row[entry.key];
      final expected = entry.value;

      if (expected is List) {
        if (!expected.contains(fieldValue)) return false;
      } else {
        if (fieldValue != expected) return false;
      }
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? '항목';

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
              onPressed: _addRow,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('추가'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        if (_rows.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '항목을 추가하세요',
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
                rows: List.generate(_rows.length, (index) {
                  final row = _rows[index];
                  return DataRow(
                    cells: [
                      ..._columns.map(
                        (col) => DataCell(
                          _isColumnVisible(col, row)
                              ? _buildCellWidget(col, row, index)
                              : const SizedBox.shrink(),
                        ),
                      ),
                      DataCell(
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 20),
                          color: Colors.red[400],
                          onPressed: () => _removeRow(index),
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

  /// 컬럼 타입에 따른 입력 위젯 생성
  Widget _buildCellWidget(_ColSchema col, Map<String, dynamic> row, int rowIndex) {
    switch (col.type) {
      case 'ENUM':
        final currentValue = row[col.name]?.toString();
        final items = col.enumValues ?? [];
        return SizedBox(
          width: 130,
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

      case 'BOOLEAN':
        return Checkbox(
          value: row[col.name] == true,
          onChanged: (value) {
            _updateCell(rowIndex, col.name, value ?? false);
          },
        );

      case 'NUMBER':
      case 'INTEGER':
        return SizedBox(
          width: 100,
          child: TextFormField(
            initialValue: row[col.name]?.toString() ?? '',
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
          width: 140,
          child: TextFormField(
            initialValue: row[col.name]?.toString() ?? '',
            decoration: InputDecoration(
              hintText: col.displayName,
              border: InputBorder.none,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(vertical: 8),
            ),
            onChanged: (value) {
              _updateCell(rowIndex, col.name, value);
            },
          ),
        );
    }
  }
}

/// 컬럼 스키마 정의
class _ColSchema {
  const _ColSchema({
    required this.name,
    required this.displayName,
    required this.type,
    this.enumValues,
    this.enumLabels,
    this.defaultValue,
    this.visibleWhen,
  });

  final String name;
  final String displayName;
  final String type;
  final List<String>? enumValues;
  final Map<String, String>? enumLabels;
  final dynamic defaultValue;
  final Map<String, dynamic>? visibleWhen;
}
