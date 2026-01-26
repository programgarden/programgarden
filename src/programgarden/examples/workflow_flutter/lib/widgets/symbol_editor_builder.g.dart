// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'symbol_editor_builder.dart';

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

class SymbolEditorBuilder extends _SymbolEditorBuilder {
  const SymbolEditorBuilder({required super.args});

  static const kType = 'symbol_editor';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static SymbolEditorBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => SymbolEditorBuilder(args: map);

  @override
  SymbolEditorBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = SymbolEditorBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _SymbolEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _SymbolEditor(
      bindableSources: model.bindableSources,
      data: data,
      decoration: model.decoration,
      expressionHint: model.expressionHint,
      expressionMode: model.expressionMode,
      initialValue: model.initialValue,
      key: key,
      objectSchema: model.objectSchema,
      uiOptions: model.uiOptions,
    );
  }
}

class JsonSymbolEditor extends JsonWidgetData {
  JsonSymbolEditor({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.bindableSources,
    this.decoration,
    this.expressionHint,
    this.expressionMode,
    this.initialValue,
    this.objectSchema,
    this.uiOptions,
  }) : super(
         jsonWidgetArgs: SymbolEditorBuilderModel.fromDynamic(
           {
             'bindableSources': bindableSources,
             'decoration': decoration,
             'expressionHint': expressionHint,
             'expressionMode': expressionMode,
             'initialValue': initialValue,
             'objectSchema': objectSchema,
             'uiOptions': uiOptions,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => SymbolEditorBuilder(
           args: SymbolEditorBuilderModel.fromDynamic(
             {
               'bindableSources': bindableSources,
               'decoration': decoration,
               'expressionHint': expressionHint,
               'expressionMode': expressionMode,
               'initialValue': initialValue,
               'objectSchema': objectSchema,
               'uiOptions': uiOptions,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: SymbolEditorBuilder.kType,
       );

  final List<dynamic>? bindableSources;

  final dynamic decoration;

  final String? expressionHint;

  final String? expressionMode;

  final dynamic initialValue;

  final List<dynamic>? objectSchema;

  final dynamic uiOptions;
}

class SymbolEditorBuilderModel extends JsonWidgetBuilderModel {
  const SymbolEditorBuilderModel(
    super.args, {
    this.bindableSources,
    this.decoration,
    this.expressionHint,
    this.expressionMode,
    this.initialValue,
    this.objectSchema,
    this.uiOptions,
  });

  final List<dynamic>? bindableSources;

  final dynamic decoration;

  final String? expressionHint;

  final String? expressionMode;

  final dynamic initialValue;

  final List<dynamic>? objectSchema;

  final dynamic uiOptions;

  static SymbolEditorBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[SymbolEditorBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static SymbolEditorBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    SymbolEditorBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is SymbolEditorBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = SymbolEditorBuilderModel(
          args,
          bindableSources: map['bindableSources'],
          decoration: map['decoration'],
          expressionHint: map['expressionHint'],
          expressionMode: map['expressionMode'],
          initialValue: map['initialValue'],
          objectSchema: map['objectSchema'],
          uiOptions: map['uiOptions'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'bindableSources': bindableSources,
      'decoration': decoration,
      'expressionHint': expressionHint,
      'expressionMode': expressionMode,
      'initialValue': initialValue,
      'objectSchema': objectSchema,
      'uiOptions': uiOptions,

      ...args,
    });
  }
}

class SymbolEditorSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/symbol_editor.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_SymbolEditor',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'bindableSources': SchemaHelper.anySchema,
      'decoration': SchemaHelper.anySchema,
      'expressionHint': SchemaHelper.stringSchema,
      'expressionMode': SchemaHelper.stringSchema,
      'initialValue': SchemaHelper.anySchema,
      'objectSchema': SchemaHelper.anySchema,
      'uiOptions': SchemaHelper.anySchema,
    },
  };
}
