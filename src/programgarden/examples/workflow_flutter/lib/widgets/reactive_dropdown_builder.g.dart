// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'reactive_dropdown_builder.dart';

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

class DropdownButtonFormFieldBuilder extends _DropdownButtonFormFieldBuilder {
  const DropdownButtonFormFieldBuilder({required super.args});

  static const kType = 'dropdown_button_form_field';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static DropdownButtonFormFieldBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => DropdownButtonFormFieldBuilder(args: map);

  @override
  DropdownButtonFormFieldBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = DropdownButtonFormFieldBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _DropdownButtonFormField buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _DropdownButtonFormField(
      data: data,
      decoration: model.decoration,
      fieldKey: model.fieldKey,
      itemLabels: model.itemLabels,
      items: model.items,
      key: key,
      validators: model.validators,
      value: model.value,
    );
  }
}

class JsonDropdownButtonFormField extends JsonWidgetData {
  JsonDropdownButtonFormField({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.decoration,
    this.fieldKey,
    this.itemLabels,
    required this.items,
    this.validators,
    this.value,
  }) : super(
         jsonWidgetArgs: DropdownButtonFormFieldBuilderModel.fromDynamic(
           {
             'decoration': decoration,
             'fieldKey': fieldKey,
             'itemLabels': itemLabels,
             'items': items,
             'validators': validators,
             'value': value,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => DropdownButtonFormFieldBuilder(
           args: DropdownButtonFormFieldBuilderModel.fromDynamic(
             {
               'decoration': decoration,
               'fieldKey': fieldKey,
               'itemLabels': itemLabels,
               'items': items,
               'validators': validators,
               'value': value,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: DropdownButtonFormFieldBuilder.kType,
       );

  final dynamic decoration;

  final String? fieldKey;

  final dynamic itemLabels;

  final List<dynamic> items;

  final dynamic validators;

  final dynamic value;
}

class DropdownButtonFormFieldBuilderModel extends JsonWidgetBuilderModel {
  const DropdownButtonFormFieldBuilderModel(
    super.args, {
    this.decoration,
    this.fieldKey,
    this.itemLabels,
    required this.items,
    this.validators,
    this.value,
  });

  final dynamic decoration;

  final String? fieldKey;

  final dynamic itemLabels;

  final List<dynamic> items;

  final dynamic validators;

  final dynamic value;

  static DropdownButtonFormFieldBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[DropdownButtonFormFieldBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static DropdownButtonFormFieldBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    DropdownButtonFormFieldBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is DropdownButtonFormFieldBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = DropdownButtonFormFieldBuilderModel(
          args,
          decoration: map['decoration'],
          fieldKey: map['fieldKey'],
          itemLabels: map['itemLabels'],
          items: map['items'],
          validators: map['validators'],
          value: map['value'],
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
      'itemLabels': itemLabels,
      'items': items,
      'validators': validators,
      'value': value,

      ...args,
    });
  }
}

class DropdownButtonFormFieldSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/dropdown_button_form_field.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_DropdownButtonFormField',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'decoration': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'itemLabels': SchemaHelper.anySchema,
      'items': SchemaHelper.anySchema,
      'validators': SchemaHelper.anySchema,
      'value': SchemaHelper.anySchema,
    },
  };
}
