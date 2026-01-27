// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'creatable_select_builder.dart';

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

class CreatableSelectBuilder extends _CreatableSelectBuilder {
  const CreatableSelectBuilder({required super.args});

  static const kType = 'creatable_select';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static CreatableSelectBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => CreatableSelectBuilder(args: map);

  @override
  CreatableSelectBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = CreatableSelectBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _CreatableSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _CreatableSelect(
      createLabel: model.createLabel,
      data: data,
      decoration: model.decoration,
      deletable: model.deletable,
      fieldKey: model.fieldKey,
      fileExtension: model.fileExtension,
      key: key,
      source: model.source,
    );
  }
}

class JsonCreatableSelect extends JsonWidgetData {
  JsonCreatableSelect({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.createLabel,
    this.decoration,
    this.deletable,
    this.fieldKey,
    this.fileExtension,
    this.source,
  }) : super(
         jsonWidgetArgs: CreatableSelectBuilderModel.fromDynamic(
           {
             'createLabel': createLabel,
             'decoration': decoration,
             'deletable': deletable,
             'fieldKey': fieldKey,
             'fileExtension': fileExtension,
             'source': source,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => CreatableSelectBuilder(
           args: CreatableSelectBuilderModel.fromDynamic(
             {
               'createLabel': createLabel,
               'decoration': decoration,
               'deletable': deletable,
               'fieldKey': fieldKey,
               'fileExtension': fileExtension,
               'source': source,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: CreatableSelectBuilder.kType,
       );

  final String? createLabel;

  final dynamic decoration;

  final dynamic deletable;

  final String? fieldKey;

  final String? fileExtension;

  final String? source;
}

class CreatableSelectBuilderModel extends JsonWidgetBuilderModel {
  const CreatableSelectBuilderModel(
    super.args, {
    this.createLabel,
    this.decoration,
    this.deletable,
    this.fieldKey,
    this.fileExtension,
    this.source,
  });

  final String? createLabel;

  final dynamic decoration;

  final dynamic deletable;

  final String? fieldKey;

  final String? fileExtension;

  final String? source;

  static CreatableSelectBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[CreatableSelectBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static CreatableSelectBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    CreatableSelectBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is CreatableSelectBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = CreatableSelectBuilderModel(
          args,
          createLabel: map['createLabel'],
          decoration: map['decoration'],
          deletable: map['deletable'],
          fieldKey: map['fieldKey'],
          fileExtension: map['fileExtension'],
          source: map['source'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'createLabel': createLabel,
      'decoration': decoration,
      'deletable': deletable,
      'fieldKey': fieldKey,
      'fileExtension': fileExtension,
      'source': source,

      ...args,
    });
  }
}

class CreatableSelectSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/creatable_select.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_CreatableSelect',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'createLabel': SchemaHelper.stringSchema,
      'decoration': SchemaHelper.anySchema,
      'deletable': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'fileExtension': SchemaHelper.stringSchema,
      'source': SchemaHelper.stringSchema,
    },
  };
}
