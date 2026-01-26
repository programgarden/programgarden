// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'checkbox_builder.dart';

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

class CheckboxBuilder extends _CheckboxBuilder {
  const CheckboxBuilder({required super.args});

  static const kType = 'checkbox_widget';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static CheckboxBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => CheckboxBuilder(args: map);

  @override
  CheckboxBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = CheckboxBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _CheckboxWidget buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _CheckboxWidget(
      data: data,
      fieldKey: model.fieldKey,
      key: key,
      labelText: model.labelText,
      value: model.value,
    );
  }
}

class JsonCheckboxWidget extends JsonWidgetData {
  JsonCheckboxWidget({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.fieldKey,
    this.labelText,
    this.value,
  }) : super(
         jsonWidgetArgs: CheckboxBuilderModel.fromDynamic(
           {
             'fieldKey': fieldKey,
             'labelText': labelText,
             'value': value,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => CheckboxBuilder(
           args: CheckboxBuilderModel.fromDynamic(
             {
               'fieldKey': fieldKey,
               'labelText': labelText,
               'value': value,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: CheckboxBuilder.kType,
       );

  final String? fieldKey;

  final String? labelText;

  final bool? value;
}

class CheckboxBuilderModel extends JsonWidgetBuilderModel {
  const CheckboxBuilderModel(
    super.args, {
    this.fieldKey,
    this.labelText,
    this.value,
  });

  final String? fieldKey;

  final String? labelText;

  final bool? value;

  static CheckboxBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[CheckboxBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static CheckboxBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    CheckboxBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is CheckboxBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = CheckboxBuilderModel(
          args,
          fieldKey: map['fieldKey'],
          labelText: map['labelText'],
          value: JsonClass.maybeParseBool(map['value']),
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'fieldKey': fieldKey,
      'labelText': labelText,
      'value': value,

      ...args,
    });
  }
}

class CheckboxWidgetSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/checkbox_widget.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_CheckboxWidget',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'fieldKey': SchemaHelper.stringSchema,
      'labelText': SchemaHelper.stringSchema,
      'value': SchemaHelper.boolSchema,
    },
  };
}
