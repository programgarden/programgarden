// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'code_editor_builder.dart';

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

class CodeEditorBuilder extends _CodeEditorBuilder {
  const CodeEditorBuilder({required super.args});

  static const kType = 'code_editor';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static CodeEditorBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => CodeEditorBuilder(args: map);

  @override
  CodeEditorBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = CodeEditorBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _CodeEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _CodeEditor(
      data: data,
      decoration: model.decoration,
      fieldKey: model.fieldKey,
      key: key,
      language: model.language,
    );
  }
}

class JsonCodeEditor extends JsonWidgetData {
  JsonCodeEditor({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.decoration,
    this.fieldKey,
    this.language,
  }) : super(
         jsonWidgetArgs: CodeEditorBuilderModel.fromDynamic(
           {
             'decoration': decoration,
             'fieldKey': fieldKey,
             'language': language,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => CodeEditorBuilder(
           args: CodeEditorBuilderModel.fromDynamic(
             {
               'decoration': decoration,
               'fieldKey': fieldKey,
               'language': language,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: CodeEditorBuilder.kType,
       );

  final dynamic decoration;

  final String? fieldKey;

  final String? language;
}

class CodeEditorBuilderModel extends JsonWidgetBuilderModel {
  const CodeEditorBuilderModel(
    super.args, {
    this.decoration,
    this.fieldKey,
    this.language,
  });

  final dynamic decoration;

  final String? fieldKey;

  final String? language;

  static CodeEditorBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[CodeEditorBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static CodeEditorBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    CodeEditorBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is CodeEditorBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = CodeEditorBuilderModel(
          args,
          decoration: map['decoration'],
          fieldKey: map['fieldKey'],
          language: map['language'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'decoration': decoration,
      'fieldKey': fieldKey,
      'language': language,

      ...args,
    });
  }
}

class CodeEditorSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/code_editor.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_CodeEditor',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'decoration': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'language': SchemaHelper.stringSchema,
    },
  };
}
