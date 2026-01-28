import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:json_dynamic_widget/json_dynamic_widget.dart';
import '../api_config.dart';

part 'credential_select_builder.g.dart';

/// Credential 선택 드롭다운 빌더
@jsonWidget
abstract class _CredentialSelectBuilder extends JsonWidgetBuilder {
  const _CredentialSelectBuilder({required super.args});

  @override
  _CredentialSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _CredentialSelect extends StatefulWidget {
  const _CredentialSelect({
    this.decoration,
    this.credentialTypes,
    this.onAdd,
    this.onEdit,
    super.key,
  });

  final dynamic decoration;
  final List<dynamic>? credentialTypes;
  final VoidCallback? onAdd;
  final void Function(String credentialId)? onEdit;

  @override
  State<_CredentialSelect> createState() => _CredentialSelectState();
}

class _CredentialSelectState extends State<_CredentialSelect> {
  String? _selectedValue;
  String? _selectedType;
  List<Map<String, dynamic>> _credentials = [];
  bool _isLoading = false;

  /// credential type 정보 파싱 (type_id, name 추출)
  List<Map<String, String>> get _parsedTypes {
    final types = widget.credentialTypes ?? [];
    return types.map((t) {
      if (t is Map) {
        return {
          'type_id': (t['type_id'] ?? t.toString()).toString(),
          'name': (t['name'] ?? t['type_id'] ?? t.toString()).toString(),
        };
      }
      // 레거시: 문자열만 있는 경우
      return {'type_id': t.toString(), 'name': t.toString()};
    }).toList();
  }

  String? _getTypeName(String? typeId) {
    if (typeId == null) return null;
    final found = _parsedTypes.where((t) => t['type_id'] == typeId);
    return found.isNotEmpty ? found.first['name'] : typeId;
  }

  @override
  void initState() {
    super.initState();
    final types = _parsedTypes;
    if (types.isNotEmpty) {
      _selectedType = types.first['type_id'];
    }
    _loadCredentials();
  }

  Future<void> _loadCredentials() async {
    if (_selectedType == null) return;

    setState(() => _isLoading = true);
    try {
      final response = await http.get(
        ApiConfig.uri('/api/credentials', queryParams: {'credential_type': _selectedType!}),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _credentials = List<Map<String, dynamic>>.from(
            data['credentials'] ?? [],
          );
        });
      }
    } catch (e) {
      debugPrint('Failed to load credentials: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final types = _parsedTypes;
    final dec = widget.decoration is Map
        ? Map<String, dynamic>.from(widget.decoration)
        : <String, dynamic>{};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // 타입이 2개 이상이면 타입 선택 드롭다운 표시
        if (types.length > 1) ...[
          DropdownButtonFormField<String>(
            initialValue: _selectedType,
            decoration: const InputDecoration(
              labelText: 'Credential 타입',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: types
                .map(
                  (t) => DropdownMenuItem(
                    value: t['type_id'],
                    child: Text(t['name'] ?? t['type_id'] ?? ''),
                  ),
                )
                .toList(),
            onChanged: (value) {
              setState(() {
                _selectedType = value;
                _selectedValue = null;
                _credentials = [];
              });
              _loadCredentials();
            },
          ),
          const SizedBox(height: 12),
        ],
        // Credential 선택 Row
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _selectedValue,
                decoration: InputDecoration(
                  labelText: dec['labelText'] as String? ?? 'Credential',
                  helperText: dec['helperText'] as String?,
                  border: const OutlineInputBorder(),
                  suffixIcon: _isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : null,
                ),
                items: [
                  const DropdownMenuItem(
                    value: '',
                    child: Text(
                      '(선택하세요)',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                  ..._credentials.map(
                    (cred) => DropdownMenuItem(
                      value: cred['id'] as String?,
                      child: Text(
                        cred['name'] as String? ??
                            cred['id'] as String? ??
                            'Unknown',
                      ),
                    ),
                  ),
                ],
                onChanged: (value) {
                  setState(() {
                    _selectedValue = value;
                  });
                },
                hint: Text(
                  _selectedType != null
                      ? '${_getTypeName(_selectedType)} 선택'
                      : 'Credential 선택',
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.add_circle_outline),
              tooltip: '새 Credential 추가',
              onPressed: _selectedType != null
                  ? () => _showCredentialDialog(context, isNew: true)
                  : null,
            ),
            IconButton(
              icon: const Icon(Icons.edit_outlined),
              tooltip: 'Credential 수정',
              onPressed: _selectedValue != null && _selectedValue!.isNotEmpty
                  ? () => _showCredentialDialog(context, isNew: false)
                  : null,
            ),
          ],
        ),
      ],
    );
  }

  void _showCredentialDialog(BuildContext context, {required bool isNew}) {
    if (_selectedType == null) return;

    showDialog(
      context: context,
      builder: (ctx) => _CredentialFormDialog(
        isNew: isNew,
        credentialType: _selectedType!,
        credentialId: isNew ? null : _selectedValue,
        onSaved: () {
          _loadCredentials();
        },
      ),
    );
  }
}

/// Credential 입력 폼 다이얼로그 (API 기반 동적 폼)
class _CredentialFormDialog extends StatefulWidget {
  const _CredentialFormDialog({
    required this.isNew,
    required this.credentialType,
    this.credentialId,
    this.onSaved,
  });

  final bool isNew;
  final String credentialType;
  final String? credentialId;
  final VoidCallback? onSaved;

  @override
  State<_CredentialFormDialog> createState() => _CredentialFormDialogState();
}

class _CredentialFormDialogState extends State<_CredentialFormDialog> {
  bool _isLoading = true;
  bool _isSaving = false;
  bool _showJson = false;
  String? _error;
  Map<String, dynamic>? _typeSchema;

  /// 폼 데이터 (widget_schema 기반 렌더링에서 사용)
  final Map<String, dynamic> _formData = {};

  /// 텍스트 필드용 컨트롤러
  final Map<String, TextEditingController> _controllers = {};

  @override
  void initState() {
    super.initState();
    _loadTypeSchema();
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _loadTypeSchema() async {
    try {
      final response = await http.get(
        ApiConfig.uri('/api/credential-types/${widget.credentialType}'),
      );
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _typeSchema = data;
          _isLoading = false;

          // widget_schema에서 기본값 추출
          final widgetSchema = data['widget_schema'] as Map<String, dynamic>?;
          if (widgetSchema != null) {
            _initFormDataFromWidgetSchema(widgetSchema);
          }
        });
      } else {
        setState(() {
          _error = 'Failed to load credential type schema';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  /// widget_schema에서 기본값 추출하여 _formData 초기화
  void _initFormDataFromWidgetSchema(Map<String, dynamic> schema) {
    // 새 형식: fields 배열
    final fields = schema['fields'] as List<dynamic>?;
    if (fields != null) {
      for (final field in fields) {
        if (field is Map<String, dynamic>) {
          final key = field['key'] as String?;
          final defaultValue = field['default'];
          if (key != null && defaultValue != null) {
            _formData[key] = defaultValue;
          }
        }
      }
    }
  }

  Future<void> _save() async {
    // 컨트롤러 값 수집
    for (final entry in _controllers.entries) {
      _formData[entry.key] = entry.value.text;
    }

    // name 필드가 없으면 기본값 설정
    final credentialName = (_formData['name'] as String?)?.isNotEmpty == true
        ? _formData['name'] as String
        : 'my-${widget.credentialType}';

    setState(() => _isSaving = true);
    try {
      final response = await http.post(
        ApiConfig.uri('/api/credentials'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': credentialName,
          'credential_type': widget.credentialType,
          'data': _formData,
        }),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        widget.onSaved?.call();
        if (mounted) Navigator.of(context).pop();
      } else {
        final error = json.decode(response.body);
        setState(() => _error = error['error'] ?? 'Save failed');
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _isSaving = false);
    }
  }

  /// 폼 데이터 변경 핸들러
  void _onFormDataChanged(String key, dynamic value) {
    setState(() {
      _formData[key] = value;
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          Text(_typeSchema?['icon'] ?? '🔑'),
          const SizedBox(width: 8),
          Text(widget.isNew ? '새 Credential 추가' : 'Credential 수정'),
        ],
      ),
      content: SizedBox(
        width: 500,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
            ? _buildError()
            : _buildForm(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('취소'),
        ),
        FilledButton(
          onPressed: _isSaving ? null : _save,
          child: _isSaving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.isNew ? '추가' : '저장'),
        ),
      ],
    );
  }

  Widget _buildError() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red[50],
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(_error!, style: TextStyle(color: Colors.red[700])),
    );
  }

  Widget _buildForm() {
    final widgetSchema = _typeSchema?['widget_schema'] as Map<String, dynamic>?;
    final typeName = _typeSchema?['name'] ?? widget.credentialType;
    final typeDesc = _typeSchema?['description'] ?? '';

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 타입 정보
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: Colors.blue[50],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, color: Colors.blue[700], size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        typeName,
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.blue[900],
                        ),
                      ),
                      if (typeDesc.isNotEmpty)
                        Text(
                          typeDesc,
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.blue[700],
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // widget_schema 기반 렌더링
          if (widgetSchema != null) _buildWidgetSchemaForm(widgetSchema),
          // JSON Schema 토글
          const SizedBox(height: 16),
          const Divider(),
          InkWell(
            onTap: () => setState(() => _showJson = !_showJson),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Row(
                children: [
                  Icon(
                    _showJson ? Icons.expand_less : Icons.expand_more,
                    size: 20,
                    color: Colors.grey[600],
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Credential Type JSON',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
          // JSON 표시
          if (_showJson && _typeSchema != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey[900],
                borderRadius: BorderRadius.circular(8),
              ),
              child: SelectableText(
                const JsonEncoder.withIndent('  ').convert(_typeSchema),
                style: const TextStyle(
                  fontSize: 11,
                  fontFamily: 'monospace',
                  color: Colors.lightGreenAccent,
                ),
              ),
            ),
        ],
      ),
    );
  }

  /// widget_schema 기반 폼 렌더링
  Widget _buildWidgetSchemaForm(Map<String, dynamic> schema) {
    // 새 형식: fields 배열
    final fields = schema['fields'] as List<dynamic>?;
    if (fields == null || fields.isEmpty) {
      return const Text('No fields defined');
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (int i = 0; i < fields.length; i++) ...[
          if (i > 0) const SizedBox(height: 12),
          _buildFieldWidget(fields[i] as Map<String, dynamic>),
        ],
        // 동적 필드 안내 (http_custom 등)
        if (schema['dynamic'] == true) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.orange[50],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              schema['dynamic_description'] as String? ?? '동적 필드를 추가할 수 있습니다.',
              style: TextStyle(fontSize: 12, color: Colors.orange[800]),
            ),
          ),
        ],
      ],
    );
  }

  /// 필드 타입에 따른 위젯 생성
  Widget _buildFieldWidget(Map<String, dynamic> field) {
    final key = field['key'] as String?;
    final type = field['type'] as String?;
    final label = field['label'] as String?;
    final hint = field['hint'] as String?;
    final description = field['description'] as String?;
    final defaultValue = field['default'];
    final required = field['required'] as bool? ?? false;

    switch (type) {
      case 'text':
        return _buildTextField(key, label, hint, description, required, false);
      case 'password':
        return _buildTextField(key, label, hint, description, required, true);
      case 'number':
        return _buildNumberField(
          key,
          label,
          hint,
          description,
          required,
          defaultValue,
        );
      case 'boolean':
        return _buildBooleanField(key, label, description, defaultValue);
      default:
        return _buildTextField(key, label, hint, description, required, false);
    }
  }

  Widget _buildTextField(
    String? key,
    String? label,
    String? hint,
    String? description,
    bool required,
    bool obscure,
  ) {
    if (key != null && !_controllers.containsKey(key)) {
      _controllers[key] = TextEditingController(
        text: _formData[key]?.toString() ?? '',
      );
    }

    return TextFormField(
      controller: key != null ? _controllers[key] : null,
      decoration: InputDecoration(
        labelText: label != null ? (required ? '$label *' : label) : null,
        hintText: hint,
        helperText: description,
        border: const OutlineInputBorder(),
        suffixIcon: obscure ? const Icon(Icons.visibility_off, size: 18) : null,
      ),
      obscureText: obscure,
      onChanged: (value) {
        if (key != null) {
          _formData[key] = value;
        }
      },
    );
  }

  Widget _buildNumberField(
    String? key,
    String? label,
    String? hint,
    String? description,
    bool required,
    dynamic defaultValue,
  ) {
    if (key != null && !_controllers.containsKey(key)) {
      _controllers[key] = TextEditingController(
        text: _formData[key]?.toString() ?? defaultValue?.toString() ?? '',
      );
    }

    return TextFormField(
      controller: key != null ? _controllers[key] : null,
      decoration: InputDecoration(
        labelText: label != null ? (required ? '$label *' : label) : null,
        hintText: hint,
        helperText: description,
        border: const OutlineInputBorder(),
      ),
      keyboardType: TextInputType.number,
      onChanged: (value) {
        if (key != null) {
          final parsed = int.tryParse(value) ?? double.tryParse(value);
          _formData[key] = parsed ?? value;
        }
      },
    );
  }

  Widget _buildBooleanField(
    String? key,
    String? label,
    String? description,
    dynamic defaultValue,
  ) {
    final currentValue = key != null
        ? (_formData[key] as bool? ?? (defaultValue as bool? ?? false))
        : (defaultValue as bool? ?? false);

    return CheckboxListTile(
      title: Text(label ?? ''),
      subtitle: description != null ? Text(description) : null,
      value: currentValue,
      onChanged: (value) {
        if (key != null) {
          _onFormDataChanged(key, value ?? false);
        }
      },
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: EdgeInsets.zero,
    );
  }
}
