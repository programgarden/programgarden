// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'object_array_table_builder.dart';

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

class ObjectArrayTableBuilder extends _ObjectArrayTableBuilder {
  const ObjectArrayTableBuilder({required super.args});

  static const kType = 'object_array_table';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static ObjectArrayTableBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => ObjectArrayTableBuilder(args: map);

  @override
  ObjectArrayTableBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = ObjectArrayTableBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _ObjectArrayTable buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _ObjectArrayTable(
      data: data,
      decoration: model.decoration,
      fieldKey: model.fieldKey,
      key: key,
      objectSchema: model.objectSchema,
    );
  }
}

class JsonObjectArrayTable extends JsonWidgetData {
  JsonObjectArrayTable({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.decoration,
    this.fieldKey,
    this.objectSchema,
  }) : super(
         jsonWidgetArgs: ObjectArrayTableBuilderModel.fromDynamic(
           {
             'decoration': decoration,
             'fieldKey': fieldKey,
             'objectSchema': objectSchema,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => ObjectArrayTableBuilder(
           args: ObjectArrayTableBuilderModel.fromDynamic(
             {
               'decoration': decoration,
               'fieldKey': fieldKey,
               'objectSchema': objectSchema,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: ObjectArrayTableBuilder.kType,
       );

  final dynamic decoration;

  final String? fieldKey;

  final List<dynamic>? objectSchema;
}

class ObjectArrayTableBuilderModel extends JsonWidgetBuilderModel {
  const ObjectArrayTableBuilderModel(
    super.args, {
    this.decoration,
    this.fieldKey,
    this.objectSchema,
  });

  final dynamic decoration;

  final String? fieldKey;

  final List<dynamic>? objectSchema;

  static ObjectArrayTableBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[ObjectArrayTableBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static ObjectArrayTableBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    ObjectArrayTableBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is ObjectArrayTableBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = ObjectArrayTableBuilderModel(
          args,
          decoration: map['decoration'],
          fieldKey: map['fieldKey'],
          objectSchema: map['objectSchema'],
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
      'objectSchema': objectSchema,

      ...args,
    });
  }
}

class ObjectArrayTableSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/object_array_table.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_ObjectArrayTable',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'decoration': SchemaHelper.anySchema,
      'fieldKey': SchemaHelper.stringSchema,
      'objectSchema': SchemaHelper.anySchema,
    },
  };
}
