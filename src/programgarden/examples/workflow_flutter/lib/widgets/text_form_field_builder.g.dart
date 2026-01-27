// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'text_form_field_builder.dart';

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

class TextFormFieldOverrideBuilder extends _TextFormFieldOverrideBuilder {
  const TextFormFieldOverrideBuilder({required super.args});

  static const kType = 'text_form_field_override';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static TextFormFieldOverrideBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => TextFormFieldOverrideBuilder(args: map);

  @override
  TextFormFieldOverrideBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = TextFormFieldOverrideBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _TextFormFieldOverride buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _TextFormFieldOverride(
      data: data,
      decoration: model.decoration,
      fieldKey: model.fieldKey,
      helperText: model.helperText,
      initialValue: model.initialValue,
      key: key,
      keyboardType: model.keyboardType,
      maxLines: model.maxLines,
      validators: model.validators,
    );
  }
}

class JsonTextFormFieldOverride extends JsonWidgetData {
  JsonTextFormFieldOverride({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.decoration,
    this.fieldKey,
    this.helperText,
    this.initialValue,
    this.keyboardType,
    this.maxLines,
    this.validators,
  }) : super(
         jsonWidgetArgs: TextFormFieldOverrideBuilderModel.fromDynamic(
           {
             'decoration': decoration,
             'fieldKey': fieldKey,
             'helperText': helperText,
             'initialValue': initialValue,
             'keyboardType': keyboardType,
             'maxLines': maxLines,
             'validators': validators,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => TextFormFieldOverrideBuilder(
           args: TextFormFieldOverrideBuilderModel.fromDynamic(
             {
               'decoration': decoration,
               'fieldKey': fieldKey,
               'helperText': helperText,
               'initialValue': initialValue,
               'keyboardType': keyboardType,
               'maxLines': maxLines,
               'validators': validators,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: TextFormFieldOverrideBuilder.kType,
       );

  final dynamic decoration;

  final String? fieldKey;

  final String? helperText;

  final String? initialValue;

  final String? keyboardType;

  final dynamic maxLines;

  final dynamic validators;
}

class TextFormFieldOverrideBuilderModel extends JsonWidgetBuilderModel {
  const TextFormFieldOverrideBuilderModel(
    super.args, {
    this.decoration,
    this.fieldKey,
    this.helperText,
    this.initialValue,
    this.keyboardType,
    this.maxLines,
    this.validators,
  });

  final dynamic decoration;

  final String? fieldKey;

  final String? helperText;

  final String? initialValue;

  final String? keyboardType;

  final dynamic maxLines;

  final dynamic validators;

  static TextFormFieldOverrideBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[TextFormFieldOverrideBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static TextFormFieldOverrideBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    TextFormFieldOverrideBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is TextFormFieldOverrideBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = TextFormFieldOverrideBuilderModel(
          args,
          decoration: map['decoration'],
          fieldKey: map['fieldKey'],
          helperText: map['helperText'],
          initialValue: map['initialValue'],
          keyboardType: map['keyboardType'],
          maxLines: map['maxLines'],
          validators: map['validators'],
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
      'helperText': helperText,
      'initialValue': initialValue,
      'keyboardType': keyboardType,
      'maxLines': maxLines,
      'validators': validators,

      ...args,
    });
  }
}

class TextFormFieldOverrideSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/text_form_field_override.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_TextFormFieldOverride',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'decoration': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'helperText': SchemaHelper.stringSchema,
      'initialValue': SchemaHelper.stringSchema,
      'keyboardType': SchemaHelper.stringSchema,
      'maxLines': SchemaHelper.anySchema,
      'validators': SchemaHelper.anySchema,
    },
  };
}
