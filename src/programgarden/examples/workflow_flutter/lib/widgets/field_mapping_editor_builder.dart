import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';

part 'field_mapping_editor_builder.g.dart';

/// 필드 매핑 에디터 빌더
///
/// from->to 필드 매핑 테이블 (FieldMappingNode.mappings)
/// to 필드에 Autocomplete 지원
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_field_mapping_editor",
///   "args": {
///     "decoration": {"labelText": "필드 매핑"},
///     "objectSchema": [
///       {"name": "from", "type": "STRING", "display_name": "원본 필드"},
///       {"name": "to", "type": "STRING", "display_name": "대상 필드",
///        "suggestions": ["symbol", "exchange", "price", "quantity"]}
///     ]
///   }
/// }
/// ```
@jsonWidget
abstract class _FieldMappingEditorBuilder extends JsonWidgetBuilder {
  const _FieldMappingEditorBuilder({required super.args});

  @override
  _FieldMappingEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _FieldMappingEditor extends StatefulWidget {
  const _FieldMappingEditor({
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
  State<_FieldMappingEditor> createState() => _FieldMappingEditorState();
}

class _FieldMappingEditorState extends State<_FieldMappingEditor> {
  final List<Map<String, String>> _mappings = [];
  late List<_MappingCol> _columns;
  late List<String> _suggestions;

  @override
  void initState() {
    super.initState();
    _columns = _parseColumns();
    _suggestions = _parseSuggestions();
  }

  List<_MappingCol> _parseColumns() {
    final schema = widget.objectSchema;
    if (schema == null || schema.isEmpty) {
      return [
        _MappingCol(name: 'from', displayName: '원본 필드'),
        _MappingCol(name: 'to', displayName: '대상 필드'),
      ];
    }

    return schema.map((col) {
      if (col is Map) {
        final map = Map<String, dynamic>.from(col);
        return _MappingCol(
          name: map['name'] as String? ?? '',
          displayName: (map['display_name'] as String?) ??
              (map['name'] as String? ?? '').replaceAll('_', ' '),
          suggestions: map['suggestions'] is List
              ? List<String>.from(map['suggestions'])
              : null,
        );
      }
      return _MappingCol(name: '', displayName: '');
    }).toList();
  }

  /// 모든 컬럼의 suggestions를 수집
  List<String> _parseSuggestions() {
    final allSuggestions = <String>[];
    for (final col in _columns) {
      if (col.suggestions != null) {
        allSuggestions.addAll(col.suggestions!);
      }
    }
    return allSuggestions.toSet().toList();
  }

  void _addMapping() {
    setState(() {
      final mapping = <String, String>{};
      for (final col in _columns) {
        mapping[col.name] = '';
      }
      _mappings.add(mapping);
    });
    _notifyChanged();
  }

  void _removeMapping(int index) {
    setState(() {
      _mappings.removeAt(index);
    });
    _notifyChanged();
  }

  void _updateCell(int rowIndex, String colName, String value) {
    setState(() {
      _mappings[rowIndex][colName] = value;
    });
    _notifyChanged();
  }

  void _notifyChanged() {
    if (widget.fieldKey != null) {
      widget.data.jsonWidgetRegistry.setValue(widget.fieldKey!, _mappings);
    }
  }

  @override
  Widget build(BuildContext context) {
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    final labelText = dec['labelText'] as String? ?? '필드 매핑';

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
              onPressed: _addMapping,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('매핑 추가'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        if (_mappings.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(
              child: Text(
                '매핑을 추가하세요',
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
                columnSpacing: 8,
                horizontalMargin: 12,
                columns: [
                  // from 컬럼
                  if (_columns.isNotEmpty)
                    DataColumn(label: Text(_columns.first.displayName)),
                  // 화살표 컬럼
                  const DataColumn(label: Text('')),
                  // to 컬럼
                  if (_columns.length > 1)
                    DataColumn(label: Text(_columns[1].displayName)),
                  // 나머지 컬럼 (있는 경우)
                  ..._columns.skip(2).map(
                    (col) => DataColumn(label: Text(col.displayName)),
                  ),
                  // 삭제 버튼
                  const DataColumn(label: Text('')),
                ],
                rows: List.generate(_mappings.length, (index) {
                  final mapping = _mappings[index];
                  return DataRow(
                    cells: [
                      // from 필드
                      if (_columns.isNotEmpty)
                        DataCell(
                          SizedBox(
                            width: 150,
                            child: TextFormField(
                              initialValue: mapping[_columns.first.name] ?? '',
                              decoration: InputDecoration(
                                hintText: _columns.first.displayName,
                                border: InputBorder.none,
                                isDense: true,
                                contentPadding:
                                    const EdgeInsets.symmetric(vertical: 8),
                              ),
                              onChanged: (value) {
                                _updateCell(index, _columns.first.name, value);
                              },
                            ),
                          ),
                        ),
                      // 화살표
                      const DataCell(
                        Padding(
                          padding: EdgeInsets.symmetric(horizontal: 4),
                          child: Icon(
                            Icons.arrow_forward,
                            size: 18,
                            color: Colors.grey,
                          ),
                        ),
                      ),
                      // to 필드 (Autocomplete 지원)
                      if (_columns.length > 1)
                        DataCell(
                          _buildAutocompleteCell(
                            index,
                            _columns[1],
                            mapping[_columns[1].name] ?? '',
                          ),
                        ),
                      // 나머지 필드
                      ..._columns.skip(2).map(
                        (col) => DataCell(
                          SizedBox(
                            width: 140,
                            child: TextFormField(
                              initialValue: mapping[col.name] ?? '',
                              decoration: InputDecoration(
                                hintText: col.displayName,
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
                      // 삭제
                      DataCell(
                        IconButton(
                          icon: const Icon(Icons.delete_outline, size: 20),
                          color: Colors.red[400],
                          onPressed: () => _removeMapping(index),
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

  /// Autocomplete 셀 위젯
  Widget _buildAutocompleteCell(
    int rowIndex,
    _MappingCol col,
    String currentValue,
  ) {
    final colSuggestions = col.suggestions ?? _suggestions;

    if (colSuggestions.isEmpty) {
      return SizedBox(
        width: 150,
        child: TextFormField(
          initialValue: currentValue,
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

    return SizedBox(
      width: 180,
      child: Autocomplete<String>(
        optionsBuilder: (TextEditingValue textEditingValue) {
          if (textEditingValue.text.isEmpty) {
            return colSuggestions;
          }
          return colSuggestions.where(
            (s) => s.toLowerCase().contains(textEditingValue.text.toLowerCase()),
          );
        },
        initialValue: TextEditingValue(text: currentValue),
        fieldViewBuilder: (context, controller, focusNode, onSubmit) {
          return TextFormField(
            controller: controller,
            focusNode: focusNode,
            decoration: InputDecoration(
              hintText: col.displayName,
              border: InputBorder.none,
              isDense: true,
              contentPadding: const EdgeInsets.symmetric(vertical: 8),
            ),
            onChanged: (value) {
              _updateCell(rowIndex, col.name, value);
            },
            onFieldSubmitted: (_) => onSubmit(),
          );
        },
        onSelected: (value) {
          _updateCell(rowIndex, col.name, value);
        },
      ),
    );
  }
}

/// 매핑 컬럼 정의
class _MappingCol {
  const _MappingCol({
    required this.name,
    required this.displayName,
    this.suggestions,
  });

  final String name;
  final String displayName;
  final List<String>? suggestions;
}
