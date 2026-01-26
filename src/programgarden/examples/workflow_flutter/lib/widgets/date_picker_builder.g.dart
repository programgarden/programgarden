// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'date_picker_builder.dart';

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

class DatePickerBuilder extends _DatePickerBuilder {
  const DatePickerBuilder({required super.args});

  static const kType = 'date_picker';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static DatePickerBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => DatePickerBuilder(args: map);

  @override
  DatePickerBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = DatePickerBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _DatePicker buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _DatePicker(
      data: data,
      dateFormat: model.dateFormat,
      decoration: model.decoration,
      fieldKey: model.fieldKey,
      firstDate: model.firstDate,
      initialValue: model.initialValue,
      key: key,
      lastDate: model.lastDate,
    );
  }
}

class JsonDatePicker extends JsonWidgetData {
  JsonDatePicker({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.dateFormat,
    this.decoration,
    required this.fieldKey,
    this.firstDate,
    this.initialValue,
    this.lastDate,
  }) : super(
         jsonWidgetArgs: DatePickerBuilderModel.fromDynamic(
           {
             'dateFormat': dateFormat,
             'decoration': decoration,
             'fieldKey': fieldKey,
             'firstDate': firstDate,
             'initialValue': initialValue,
             'lastDate': lastDate,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => DatePickerBuilder(
           args: DatePickerBuilderModel.fromDynamic(
             {
               'dateFormat': dateFormat,
               'decoration': decoration,
               'fieldKey': fieldKey,
               'firstDate': firstDate,
               'initialValue': initialValue,
               'lastDate': lastDate,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: DatePickerBuilder.kType,
       );

  final String? dateFormat;

  final dynamic decoration;

  final String fieldKey;

  final String? firstDate;

  final String? initialValue;

  final String? lastDate;
}

class DatePickerBuilderModel extends JsonWidgetBuilderModel {
  const DatePickerBuilderModel(
    super.args, {
    this.dateFormat,
    this.decoration,
    required this.fieldKey,
    this.firstDate,
    this.initialValue,
    this.lastDate,
  });

  final String? dateFormat;

  final dynamic decoration;

  final String fieldKey;

  final String? firstDate;

  final String? initialValue;

  final String? lastDate;

  static DatePickerBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[DatePickerBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static DatePickerBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    DatePickerBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is DatePickerBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = DatePickerBuilderModel(
          args,
          dateFormat: map['dateFormat'],
          decoration: map['decoration'],
          fieldKey: map['fieldKey'],
          firstDate: map['firstDate'],
          initialValue: map['initialValue'],
          lastDate: map['lastDate'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'dateFormat': dateFormat,
      'decoration': decoration,
      'fieldKey': fieldKey,
      'firstDate': firstDate,
      'initialValue': initialValue,
      'lastDate': lastDate,

      ...args,
    });
  }
}

class DatePickerSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/date_picker.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_DatePicker',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'dateFormat': SchemaHelper.stringSchema,
      'decoration': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'firstDate': SchemaHelper.stringSchema,
      'initialValue': SchemaHelper.stringSchema,
      'lastDate': SchemaHelper.stringSchema,
    },
  };
}
