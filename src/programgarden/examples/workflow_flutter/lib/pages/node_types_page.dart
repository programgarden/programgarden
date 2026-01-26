import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:json_dynamic_widget/json_dynamic_widget.dart';
import '../widgets/checkbox_builder.dart';
import '../widgets/credential_select_builder.dart';
import '../widgets/date_picker_builder.dart';
import '../widgets/plugin_select_builder.dart';
import '../widgets/symbol_editor_builder.dart';
import '../widgets/reactive_dropdown_builder.dart';
import '../widgets/expression_toggle_builder.dart';

/// ProgramGarden 커스텀 위젯 레지스트리
/// json_dynamic_widget에서 지원하지 않는 커스텀 위젯들을 등록합니다.
class ProgramGardenWidgetRegistry {
  static JsonWidgetRegistry? _instance;

  static JsonWidgetRegistry get instance {
    if (_instance == null) {
      _instance = JsonWidgetRegistry.instance.copyWith();
      _registerCustomWidgets(_instance!);
    }
    return _instance!;
  }

  /// 새로운 registry 인스턴스 생성 (폼별 독립적인 상태 관리용)
  static JsonWidgetRegistry createInstance() {
    final registry = JsonWidgetRegistry.instance.copyWith();
    _registerCustomWidgets(registry);
    return registry;
  }

  static void _registerCustomWidgets(JsonWidgetRegistry registry) {
    // dropdown_button_form_field: 반응형 드롭다운 (기본 위젯 오버라이드)
    // 값 변경 시 registry.setValue() 호출 → 내장 conditional 위젯이 감시
    // ⚠️ 같은 키로 등록하면 기존 빌더를 덮어씁니다 (_builders[type] = container)
    debugPrint('🔥🔥🔥 [Registry] _registerCustomWidgets called!');
    debugPrint(
      '🔥 [Registry] Registering DropdownButtonFormFieldBuilder: ${DropdownButtonFormFieldBuilder.kType}',
    );
    registry.registerCustomBuilder(
      DropdownButtonFormFieldBuilder.kType,
      JsonWidgetBuilderContainer(
        builder: DropdownButtonFormFieldBuilder.fromDynamic,
      ),
    );
    debugPrint(
      '🔥 [Registry] DropdownButtonFormFieldBuilder registered successfully',
    );

    // custom_credential_select: Credential 선택 드롭다운
    registry.registerCustomBuilder(
      'custom_${CredentialSelectBuilder.kType}',
      JsonWidgetBuilderContainer(builder: CredentialSelectBuilder.fromDynamic),
    );

    // custom_plugin_select: Plugin 선택 드롭다운
    registry.registerCustomBuilder(
      'custom_${PluginSelectBuilder.kType}',
      JsonWidgetBuilderContainer(builder: PluginSelectBuilder.fromDynamic),
    );

    // custom_symbol_editor: 종목 에디터
    registry.registerCustomBuilder(
      'custom_${SymbolEditorBuilder.kType}',
      JsonWidgetBuilderContainer(builder: SymbolEditorBuilder.fromDynamic),
    );

    // custom_expression_toggle: Fixed/Expression 토글
    registry.registerCustomBuilder(
      'custom_${ExpressionToggleBuilder.kType}',
      JsonWidgetBuilderContainer(builder: ExpressionToggleBuilder.fromDynamic),
    );

    // checkbox: helperText 지원 체크박스 (기본 위젯 오버라이드)
    // 서버에서 type: "checkbox"로 보내므로 'checkbox'로 등록
    registry.registerCustomBuilder(
      'checkbox',
      JsonWidgetBuilderContainer(builder: CheckboxBuilder.fromDynamic),
    );

    // custom_date_picker: 날짜 선택 위젯
    registry.registerCustomBuilder(
      'custom_${DatePickerBuilder.kType}',
      JsonWidgetBuilderContainer(builder: DatePickerBuilder.fromDynamic),
    );
  }
}

/// 카테고리 순서 정의
const List<String> categoryOrder = [
  'infra',
  'account',
  'market',
  'condition',
  'order',
  'risk',
  'schedule',
  'data',
  'analysis',
  'system',
  'messaging',
];

/// 카테고리 한글명
const Map<String, String> categoryNames = {
  'infra': '인프라',
  'account': '계좌',
  'market': '시장/시세',
  'condition': '조건',
  'order': '주문',
  'risk': '리스크',
  'schedule': '스케줄',
  'data': '데이터',
  'analysis': '분석',
  'system': '시스템',
  'messaging': '메시징',
};

/// JSON으로 위젯을 동적 렌더링하는 별도 위젯
/// conditional 위젯을 위해 registry 값 변경을 추적합니다.
class JsonDynamicWidgetBuilder extends StatefulWidget {
  const JsonDynamicWidgetBuilder({
    super.key,
    required this.jsonData,
    this.registry,
  });

  final Map<String, dynamic> jsonData;
  final JsonWidgetRegistry? registry;

  @override
  State<JsonDynamicWidgetBuilder> createState() =>
      _JsonDynamicWidgetBuilderState();
}

class _JsonDynamicWidgetBuilderState extends State<JsonDynamicWidgetBuilder> {
  late JsonWidgetRegistry _registry;
  late Map<String, dynamic> _processedJson;

  @override
  void initState() {
    super.initState();
    // 각 폼마다 독립적인 registry 인스턴스 사용
    _registry = widget.registry ?? ProgramGardenWidgetRegistry.createInstance();
    _processedJson = _preprocessJson(widget.jsonData);
    _initializeDefaultValues();
  }

  @override
  void didUpdateWidget(JsonDynamicWidgetBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.jsonData != oldWidget.jsonData) {
      _processedJson = _preprocessJson(widget.jsonData);
      _initializeDefaultValues();
    }
  }

  /// JSON 전처리: dropdown 위젯에 onChanged 콜백 추가
  Map<String, dynamic> _preprocessJson(Map<String, dynamic> json) {
    return _processWidget(Map<String, dynamic>.from(json));
  }

  Map<String, dynamic> _processWidget(Map<String, dynamic> widget) {
    final result = Map<String, dynamic>.from(widget);

    // children 처리
    if (result['args'] != null && result['args']['children'] != null) {
      final children = result['args']['children'] as List;
      result['args'] = Map<String, dynamic>.from(result['args']);
      result['args']['children'] = children.map((child) {
        if (child is Map<String, dynamic>) {
          return _processWidget(child);
        }
        return child;
      }).toList();
    }

    // onTrue/onFalse 처리 (conditional 위젯)
    if (result['args'] != null) {
      final args = result['args'] as Map<String, dynamic>;
      if (args['onTrue'] != null && args['onTrue'] is Map<String, dynamic>) {
        result['args'] = Map<String, dynamic>.from(args);
        result['args']['onTrue'] = _processWidget(
          args['onTrue'] as Map<String, dynamic>,
        );
      }
      if (args['onFalse'] != null && args['onFalse'] is Map<String, dynamic>) {
        result['args'] = Map<String, dynamic>.from(result['args']);
        result['args']['onFalse'] = _processWidget(
          args['onFalse'] as Map<String, dynamic>,
        );
      }
    }

    return result;
  }

  /// 기본값 초기화: 드롭다운의 기본값을 registry에 저장
  void _initializeDefaultValues() {
    _extractDefaultValues(widget.jsonData);
  }

  void _extractDefaultValues(Map<String, dynamic> json) {
    final type = json['type'] as String?;
    final args = json['args'] as Map<String, dynamic>?;
    final fieldKey = json['field_key_of_pydantic'] as String?;

    // dropdown의 기본값 저장
    if (type == 'dropdown_button_form_field' &&
        fieldKey != null &&
        args != null) {
      final defaultValue = args['value'];
      if (defaultValue != null) {
        _registry.setValue(fieldKey, defaultValue);
      }
    }

    // children 순회
    if (args != null && args['children'] != null) {
      final children = args['children'] as List;
      for (final child in children) {
        if (child is Map<String, dynamic>) {
          _extractDefaultValues(child);
        }
      }
    }

    // conditional의 onTrue/onFalse 순회
    if (args != null) {
      if (args['onTrue'] is Map<String, dynamic>) {
        _extractDefaultValues(args['onTrue'] as Map<String, dynamic>);
      }
      if (args['onFalse'] is Map<String, dynamic>) {
        _extractDefaultValues(args['onFalse'] as Map<String, dynamic>);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    try {
      final data = JsonWidgetData.fromDynamic(
        _processedJson,
        registry: _registry,
      );
      return _FormStateWrapper(
        registry: _registry,
        child: data.build(context: context, registry: _registry),
      );
    } catch (e) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.orange[50],
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.orange),
        ),
        child: Text(
          '위젯 렌더링 실패: $e\n\n커스텀 위젯 타입은 아직 지원되지 않습니다.',
          style: TextStyle(color: Colors.orange[900], fontSize: 12),
        ),
      );
    }
  }
}

/// 폼 상태 래퍼: 하위 위젯에서 registry에 접근할 수 있도록 InheritedWidget 제공
class _FormStateWrapper extends StatelessWidget {
  const _FormStateWrapper({required this.registry, required this.child});

  final JsonWidgetRegistry registry;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return FormRegistryProvider(registry: registry, child: child);
  }
}

/// InheritedWidget으로 registry를 하위 위젯에 전달
class FormRegistryProvider extends InheritedWidget {
  const FormRegistryProvider({
    super.key,
    required this.registry,
    required super.child,
  });

  final JsonWidgetRegistry registry;

  static FormRegistryProvider? of(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<FormRegistryProvider>();
  }

  @override
  bool updateShouldNotify(FormRegistryProvider oldWidget) {
    return registry != oldWidget.registry;
  }
}

class NodeTypesPage extends StatefulWidget {
  const NodeTypesPage({super.key});

  @override
  State<NodeTypesPage> createState() => _NodeTypesPageState();
}

class _NodeTypesPageState extends State<NodeTypesPage> {
  // API 데이터 상태
  List<Map<String, dynamic>> _nodeTypes = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchNodeTypes();
  }

  /// API에서 노드 타입 스키마 가져오기
  Future<void> _fetchNodeTypes() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await http.get(
        Uri.parse('http://localhost:8766/api/node-types?locale=ko'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final nodeTypes =
            (data['node_types'] as List?)?.cast<Map<String, dynamic>>() ?? [];

        setState(() {
          _nodeTypes = nodeTypes;
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'API 오류: ${response.statusCode}';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage =
            '연결 오류: $e\n\n서버 실행: cd python_server && python server.py';
        _isLoading = false;
      });
    }
  }

  /// 카테고리별로 노드 그룹화
  Map<String, List<Map<String, dynamic>>> _groupByCategory() {
    final grouped = <String, List<Map<String, dynamic>>>{};
    for (final node in _nodeTypes) {
      final category = node['category'] as String? ?? 'other';
      grouped.putIfAbsent(category, () => []).add(node);
    }
    return grouped;
  }

  /// 노드 상세 다이얼로그 표시
  void _showNodeDetailDialog(Map<String, dynamic> node) {
    showDialog(
      context: context,
      builder: (context) => NodeDetailDialog(node: node),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('노드 종류보기'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchNodeTypes,
            tooltip: '새로고침',
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.red[50],
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.red),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, color: Colors.red[700], size: 48),
              const SizedBox(height: 16),
              Text(
                _errorMessage!,
                style: TextStyle(color: Colors.red[900]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _fetchNodeTypes,
                icon: const Icon(Icons.refresh),
                label: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }

    final grouped = _groupByCategory();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 총 노드 수 표시
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue[50],
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, color: Colors.blue[700]),
                const SizedBox(width: 8),
                Text(
                  '총 ${_nodeTypes.length}개 노드 타입',
                  style: TextStyle(
                    color: Colors.blue[900],
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // 카테고리별 노드 표시
          ...categoryOrder
              .where((cat) => grouped.containsKey(cat))
              .map(
                (category) =>
                    _buildCategorySection(category, grouped[category]!),
              ),

          // 기타 카테고리 (정의되지 않은 카테고리)
          ...grouped.keys
              .where((cat) => !categoryOrder.contains(cat))
              .map(
                (category) =>
                    _buildCategorySection(category, grouped[category]!),
              ),
        ],
      ),
    );
  }

  Widget _buildCategorySection(
    String category,
    List<Map<String, dynamic>> nodes,
  ) {
    final categoryName = categoryNames[category] ?? category;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // 카테고리 헤더
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
          decoration: BoxDecoration(
            color: Colors.indigo[100],
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(_getCategoryIcon(category), color: Colors.indigo[700]),
              const SizedBox(width: 8),
              Text(
                '$categoryName ($category)',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Colors.indigo[900],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.indigo[700],
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${nodes.length}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // 노드 카드 그리드
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: nodes.map((node) => _buildNodeCard(node)).toList(),
        ),

        const SizedBox(height: 24),
      ],
    );
  }

  IconData _getCategoryIcon(String category) {
    switch (category) {
      case 'infra':
        return Icons.settings;
      case 'account':
        return Icons.account_balance;
      case 'market':
        return Icons.show_chart;
      case 'condition':
        return Icons.rule;
      case 'order':
        return Icons.shopping_cart;
      case 'risk':
        return Icons.shield;
      case 'schedule':
        return Icons.schedule;
      case 'data':
        return Icons.storage;
      case 'analysis':
        return Icons.analytics;
      case 'system':
        return Icons.computer;
      case 'messaging':
        return Icons.message;
      default:
        return Icons.extension;
    }
  }

  Widget _buildNodeCard(Map<String, dynamic> node) {
    final nodeType = node['node_type'] as String? ?? 'Unknown';
    final description = node['description'] as String? ?? '';
    final category = node['category'] as String? ?? '';
    final hasWidgetSchema = node['widget_schema'] != null;

    return InkWell(
      onTap: () => _showNodeDetailDialog(node),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 280,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey[300]!),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 노드명 및 배지
            Row(
              children: [
                Expanded(
                  child: Text(
                    nodeType,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                ),
                if (hasWidgetSchema)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.green[100],
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '설정',
                      style: TextStyle(fontSize: 10, color: Colors.green[800]),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),

            // 카테고리 배지
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.grey[200],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                category,
                style: TextStyle(fontSize: 10, color: Colors.grey[700]),
              ),
            ),
            const SizedBox(height: 8),

            // 설명
            if (description.isNotEmpty)
              Text(
                description,
                style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),

            const Divider(height: 16),

            // JSON 미리보기
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _formatNodeJson(node),
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 9,
                      color: Colors.black87,
                    ),
                    maxLines: 5,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Align(
                    alignment: Alignment.centerRight,
                    child: InkWell(
                      onTap: () => _showFullJsonDialog(context, node),
                      child: Text(
                        '전체보기 →',
                        style: TextStyle(
                          fontSize: 10,
                          color: Colors.blue[700],
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatNodeJson(Map<String, dynamic> node, {bool full = false}) {
    // 노드 정보 원본 그대로 표시
    final preview = {
      'type': node['node_type'],
      'category': node['category'],
      'inputs': node['inputs'] ?? [],
      'outputs': node['outputs'] ?? [],
      if (full && node['widget_schema'] != null)
        'widget_schema': node['widget_schema'],
    };
    return const JsonEncoder.withIndent('  ').convert(preview);
  }

  void _showFullJsonDialog(BuildContext context, Map<String, dynamic> node) {
    final fullJson = _formatNodeJson(node, full: true);
    showDialog(
      context: context,
      builder: (context) => Dialog(
        child: Container(
          width: 700,
          constraints: BoxConstraints(
            maxHeight: MediaQuery.of(context).size.height * 0.85,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // 헤더
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey[100],
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(12),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(Icons.code, color: Colors.grey[700]),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${node['node_type']} 전체 스키마',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ],
                ),
              ),
              // JSON 내용
              Flexible(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: SelectableText(
                    fullJson,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: Colors.black87,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 노드 상세 다이얼로그
class NodeDetailDialog extends StatefulWidget {
  const NodeDetailDialog({super.key, required this.node});

  final Map<String, dynamic> node;

  @override
  State<NodeDetailDialog> createState() => _NodeDetailDialogState();
}

class _NodeDetailDialogState extends State<NodeDetailDialog>
    with SingleTickerProviderStateMixin {
  late TabController? _tabController;
  bool _hasSettingsTab = false;

  @override
  void initState() {
    super.initState();
    // settings_widget_schema가 있으면 탭 표시
    _hasSettingsTab = widget.node['settings_widget_schema'] != null;
    if (_hasSettingsTab) {
      _tabController = TabController(length: 2, vsync: this);
    } else {
      _tabController = null;
    }
  }

  @override
  void dispose() {
    _tabController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final nodeType = widget.node['node_type'] as String? ?? 'Unknown';
    final description = widget.node['description'] as String? ?? '';
    final widgetSchema = widget.node['widget_schema'] as Map<String, dynamic>?;
    final settingsWidgetSchema =
        widget.node['settings_widget_schema'] as Map<String, dynamic>?;
    final inputs = widget.node['inputs'] as List? ?? [];
    final outputs = widget.node['outputs'] as List? ?? [];

    return Dialog(
      child: Container(
        width: 600,
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.85,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 헤더
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.indigo[50],
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(12),
                ),
              ),
              child: Row(
                children: [
                  Icon(Icons.widgets, color: Colors.indigo[700]),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '$nodeType 설정',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Colors.indigo[900],
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            // 본문 (스크롤 가능)
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 설명
                    if (description.isNotEmpty) ...[
                      Text(
                        description,
                        style: TextStyle(color: Colors.grey[700], fontSize: 14),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // 입출력 정보
                    Row(
                      children: [
                        _buildPortBadge('입력', inputs.length, Colors.blue),
                        const SizedBox(width: 8),
                        _buildPortBadge('출력', outputs.length, Colors.green),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // widget_schema 기반 폼 렌더링 (탭 UI)
                    _buildFormSection(widgetSchema, settingsWidgetSchema),

                    const SizedBox(height: 24),

                    // 입력 포트 목록
                    if (inputs.isNotEmpty) ...[
                      _buildSectionHeader('입력 포트'),
                      const SizedBox(height: 8),
                      ...inputs.map(
                        (input) => _buildPortItem(
                          input as Map<String, dynamic>,
                          Colors.blue,
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // 출력 포트 목록
                    if (outputs.isNotEmpty) ...[
                      _buildSectionHeader('출력 포트'),
                      const SizedBox(height: 8),
                      ...outputs.map(
                        (output) => _buildPortItem(
                          output as Map<String, dynamic>,
                          Colors.green,
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // JSON 미리보기
                    _buildSectionHeader('전체 JSON'),
                    const SizedBox(height: 8),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.grey[100],
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: SelectableText(
                        const JsonEncoder.withIndent('  ').convert(widget.node),
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // 푸터
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.grey[100],
                borderRadius: const BorderRadius.vertical(
                  bottom: Radius.circular(12),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('닫기'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// 폼 섹션 빌드 (탭 UI 또는 단일 뷰)
  Widget _buildFormSection(
    Map<String, dynamic>? widgetSchema,
    Map<String, dynamic>? settingsWidgetSchema,
  ) {
    // 둘 다 없으면 "설정할 필드가 없습니다"
    if (widgetSchema == null && settingsWidgetSchema == null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey[100],
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: Colors.grey[600]),
            const SizedBox(width: 8),
            Text('설정할 필드가 없습니다', style: TextStyle(color: Colors.grey[600])),
          ],
        ),
      );
    }

    // settings_widget_schema가 없으면 단일 뷰
    if (!_hasSettingsTab) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSectionHeader('설정 폼'),
          const SizedBox(height: 8),
          if (widgetSchema != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey[300]!),
                borderRadius: BorderRadius.circular(8),
              ),
              child: JsonDynamicWidgetBuilder(jsonData: widgetSchema),
            ),
        ],
      );
    }

    // 탭 UI
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionHeader('설정 폼'),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey[300]!),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            children: [
              // 탭 바
              Container(
                decoration: BoxDecoration(
                  color: Colors.grey[50],
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(8),
                  ),
                ),
                child: TabBar(
                  controller: _tabController,
                  labelColor: Colors.indigo[700],
                  unselectedLabelColor: Colors.grey[600],
                  indicatorColor: Colors.indigo[700],
                  indicatorSize: TabBarIndicatorSize.tab,
                  tabs: const [
                    Tab(text: '기본 설정'),
                    Tab(text: '고급 설정'),
                  ],
                ),
              ),
              // 탭 내용
              SizedBox(
                height: 300, // 적절한 높이 지정
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    // 기본 설정 탭
                    SingleChildScrollView(
                      padding: const EdgeInsets.all(12),
                      child: widgetSchema != null
                          ? JsonDynamicWidgetBuilder(jsonData: widgetSchema)
                          : Center(
                              child: Text(
                                '기본 설정 필드가 없습니다',
                                style: TextStyle(color: Colors.grey[600]),
                              ),
                            ),
                    ),
                    // 고급 설정 탭
                    SingleChildScrollView(
                      padding: const EdgeInsets.all(12),
                      child: settingsWidgetSchema != null
                          ? JsonDynamicWidgetBuilder(
                              jsonData: settingsWidgetSchema,
                            )
                          : Center(
                              child: Text(
                                '고급 설정 필드가 없습니다',
                                style: TextStyle(color: Colors.grey[600]),
                              ),
                            ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontWeight: FontWeight.bold,
        fontSize: 14,
        color: Colors.black87,
      ),
    );
  }

  Widget _buildPortBadge(String label, int count, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 12)),
          const SizedBox(width: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$count',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPortItem(Map<String, dynamic> port, Color color) {
    final name = port['name'] as String? ?? '';
    final type = port['type'] as String? ?? '';
    final description = port['description'] as String? ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: color.withOpacity(0.05),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: color.withOpacity(0.2),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              name,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 12,
                color: color.withOpacity(0.9),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  type,
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.grey[600],
                    fontFamily: 'monospace',
                  ),
                ),
                if (description.isNotEmpty)
                  Text(
                    description,
                    style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
