import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'key_value_editor_builder.g.dart';

/// 키-값 에디터 빌더
///
/// 동적 키-값 쌍을 테이블 형태로 편집 (PortfolioNode, HTTPRequestNode, SQLiteNode)
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_key_value_editor",
///   "args": {
///     "decoration": {"labelText": "헤더"},
///     "objectSchema": [
///       {"name": "key", "type": "STRING"},
///       {"name": "value", "type": "STRING"}
///     ]
///   }
/// }
/// ```
@jsonWidget
abstract class _KeyValueEditorBuilder extends JsonWidgetBuilder {
  const _KeyValueEditorBuilder({required super.args});

  @override
  _KeyValueEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _KeyValueEditor extends StatefulWidget {
  const _KeyValueEditor({
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
  State<_KeyValueEditor> createState() => _KeyValueEditorState();
}

class _KeyValueEditorState extends State<_KeyValueEditor> {
  /// 행 데이터 [{key: '', value: ''}, ...]
  final List<Map<String, String>> _rows = [];

  /// 컬럼 정의 (objectSchema에서 파싱)
  late List<_ColumnDef> _columns;

  @override
  void initState() {
    super.initState();
    _columns = _parseColumns();
  }

  List<_ColumnDef> _parseColumns() {
    final schema = widget.objectSchema;
    if (schema == null || schema.isEmpty) {
      // 기본 key/value 2컬럼
      return [
        _ColumnDef(name: 'key', label: 'Key', type: 'STRING'),
        _ColumnDef(name: 'value', label: 'Value', type: 'STRING'),
      ];
    }

    return schema.map((col) {
      if (col is Map) {
        final map = Map<String, dynamic>.from(col);
        return _ColumnDef(
          name: map['name'] as String? ?? '',
          label: (map['display_name'] as String?) ??
              (map['name'] as String? ?? '').replaceAll('_', ' '),
          type: map['type'] as String? ?? 'STRING',
        );
      }
      return _ColumnDef(name: '', label: '', type: 'STRING');
    }).toList();
  }

  void _addRow() {
    setState(() {
      final row = <String, String>{};
      for (final col in _columns) {
        row[col.name] = '';
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

  void _updateCell(int rowIndex, String colName, String value) {
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

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? 'Key-Value';

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

        // 테이블
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
                columnSpacing: 16,
                horizontalMargin: 12,
                columns: [
                  ..._columns.map(
                    (col) => DataColumn(label: Text(col.label)),
                  ),
                  const DataColumn(label: Text('')), // 삭제 버튼 컬럼
                ],
                rows: List.generate(_rows.length, (index) {
                  final row = _rows[index];
                  return DataRow(
                    cells: [
                      ..._columns.map(
                        (col) => DataCell(
                          SizedBox(
                            width: 150,
                            child: TextFormField(
                              initialValue: row[col.name] ?? '',
                              decoration: InputDecoration(
                                hintText: col.label,
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding:
                                    const EdgeInsets.symmetric(vertical: 8),
                              ),
                              onChanged: (value) {
                                _updateCell(index, col.name, value);
                              },
                            ),
                          ),
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
}

/// 컬럼 정의
class _ColumnDef {
  const _ColumnDef({
    required this.name,
    required this.label,
    required this.type,
  });

  final String name;
  final String label;
  final String type;
}
