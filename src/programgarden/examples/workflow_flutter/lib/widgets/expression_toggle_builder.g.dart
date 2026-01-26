// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'expression_toggle_builder.dart';

// **************************************************************************
// Generator: JsonWidgetLibraryBuilder
// **************************************************************************

// ignore_for_file: avoid_init_to_null
// ignore_for_file: deprecated_member_use
// ignore_for_file: library_private_types_in_public_api
// ignore_for_file: prefer_const_constructors
// ignore_for_file: prefer_const_constructors_in_immutables
// ignore_for_file: prefer_final_locals
// ignore_for_file: prefer_if_null_operators
// ignore_for_file: prefer_single_quotes
// ignore_for_file: unused_local_variable

class ExpressionToggleBuilder extends _ExpressionToggleBuilder {
  const ExpressionToggleBuilder({required super.args});

  static const kType = 'expression_toggle';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static ExpressionToggleBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => ExpressionToggleBuilder(args: map);

  @override
  ExpressionToggleBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = ExpressionToggleBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _ExpressionToggle buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _ExpressionToggle(
      data: data,
      defaultMode: model.defaultMode,
      expressionHelperText: model.expressionHelperText,
      expressionHint: model.expressionHint,
      expressionWidget: model.expressionWidget,
      fieldKey: model.fieldKey,
      fixedHelperText: model.fixedHelperText,
      fixedWidget: model.fixedWidget,
      key: key,
      label: model.label,
      lockedMode: model.lockedMode,
    );
  }
}

class JsonExpressionToggle extends JsonWidgetData {
  JsonExpressionToggle({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.defaultMode,
    this.expressionHelperText,
    this.expressionHint,
    this.expressionWidget,
    required this.fieldKey,
    this.fixedHelperText,
    this.fixedWidget,
    this.label,
    this.lockedMode,
  }) : super(
         jsonWidgetArgs: ExpressionToggleBuilderModel.fromDynamic(
           {
             'defaultMode': defaultMode,
             'expressionHelperText': expressionHelperText,
             'expressionHint': expressionHint,
             'expressionWidget': expressionWidget,
             'fieldKey': fieldKey,
             'fixedHelperText': fixedHelperText,
             'fixedWidget': fixedWidget,
             'label': label,
             'lockedMode': lockedMode,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => ExpressionToggleBuilder(
           args: ExpressionToggleBuilderModel.fromDynamic(
             {
               'defaultMode': defaultMode,
               'expressionHelperText': expressionHelperText,
               'expressionHint': expressionHint,
               'expressionWidget': expressionWidget,
               'fieldKey': fieldKey,
               'fixedHelperText': fixedHelperText,
               'fixedWidget': fixedWidget,
               'label': label,
               'lockedMode': lockedMode,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: ExpressionToggleBuilder.kType,
       );

  final String? defaultMode;

  final String? expressionHelperText;

  final String? expressionHint;

  final dynamic expressionWidget;

  final String fieldKey;

  final String? fixedHelperText;

  final dynamic fixedWidget;

  final String? label;

  final String? lockedMode;
}

class ExpressionToggleBuilderModel extends JsonWidgetBuilderModel {
  const ExpressionToggleBuilderModel(
    super.args, {
    this.defaultMode,
    this.expressionHelperText,
    this.expressionHint,
    this.expressionWidget,
    required this.fieldKey,
    this.fixedHelperText,
    this.fixedWidget,
    this.label,
    this.lockedMode,
  });

  final String? defaultMode;

  final String? expressionHelperText;

  final String? expressionHint;

  final dynamic expressionWidget;

  final String fieldKey;

  final String? fixedHelperText;

  final dynamic fixedWidget;

  final String? label;

  final String? lockedMode;

  static ExpressionToggleBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[ExpressionToggleBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static ExpressionToggleBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    ExpressionToggleBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is ExpressionToggleBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = ExpressionToggleBuilderModel(
          args,
          defaultMode: map['defaultMode'],
          expressionHelperText: map['expressionHelperText'],
          expressionHint: map['expressionHint'],
          expressionWidget: map['expressionWidget'],
          fieldKey: map['fieldKey'],
          fixedHelperText: map['fixedHelperText'],
          fixedWidget: map['fixedWidget'],
          label: map['label'],
          lockedMode: map['lockedMode'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'defaultMode': defaultMode,
      'expressionHelperText': expressionHelperText,
      'expressionHint': expressionHint,
      'expressionWidget': expressionWidget,
      'fieldKey': fieldKey,
      'fixedHelperText': fixedHelperText,
      'fixedWidget': fixedWidget,
      'label': label,
      'lockedMode': lockedMode,

      ...args,
    });
  }
}

class ExpressionToggleSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/expression_toggle.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_ExpressionToggle',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'defaultMode': SchemaHelper.stringSchema,
      'expressionHelperText': SchemaHelper.stringSchema,
      'expressionHint': SchemaHelper.stringSchema,
      'expressionWidget': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'fixedHelperText': SchemaHelper.stringSchema,
      'fixedWidget': SchemaHelper.anySchema,
      'label': SchemaHelper.stringSchema,
      'lockedMode': SchemaHelper.stringSchema,
    },
  };
}
