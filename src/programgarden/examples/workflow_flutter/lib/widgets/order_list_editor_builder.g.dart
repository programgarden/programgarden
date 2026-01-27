// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'order_list_editor_builder.dart';

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

class OrderListEditorBuilder extends _OrderListEditorBuilder {
  const OrderListEditorBuilder({required super.args});

  static const kType = 'order_list_editor';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static OrderListEditorBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => OrderListEditorBuilder(args: map);

  @override
  OrderListEditorBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = OrderListEditorBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _OrderListEditor buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _OrderListEditor(
      bindableSources: model.bindableSources,
      data: data,
      decoration: model.decoration,
      exampleBinding: model.exampleBinding,
      fieldKey: model.fieldKey,
      key: key,
      objectSchema: model.objectSchema,
    );
  }
}

class JsonOrderListEditor extends JsonWidgetData {
  JsonOrderListEditor({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.bindableSources,
    this.decoration,
    this.exampleBinding,
    this.fieldKey,
    this.objectSchema,
  }) : super(
         jsonWidgetArgs: OrderListEditorBuilderModel.fromDynamic(
           {
             'bindableSources': bindableSources,
             'decoration': decoration,
             'exampleBinding': exampleBinding,
             'fieldKey': fieldKey,
             'objectSchema': objectSchema,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => OrderListEditorBuilder(
           args: OrderListEditorBuilderModel.fromDynamic(
             {
               'bindableSources': bindableSources,
               'decoration': decoration,
               'exampleBinding': exampleBinding,
               'fieldKey': fieldKey,
               'objectSchema': objectSchema,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: OrderListEditorBuilder.kType,
       );

  final List<dynamic>? bindableSources;

  final dynamic decoration;

  final String? exampleBinding;

  final String? fieldKey;

  final List<dynamic>? objectSchema;
}

class OrderListEditorBuilderModel extends JsonWidgetBuilderModel {
  const OrderListEditorBuilderModel(
    super.args, {
    this.bindableSources,
    this.decoration,
    this.exampleBinding,
    this.fieldKey,
    this.objectSchema,
  });

  final List<dynamic>? bindableSources;

  final dynamic decoration;

  final String? exampleBinding;

  final String? fieldKey;

  final List<dynamic>? objectSchema;

  static OrderListEditorBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[OrderListEditorBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static OrderListEditorBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    OrderListEditorBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is OrderListEditorBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = OrderListEditorBuilderModel(
          args,
          bindableSources: map['bindableSources'],
          decoration: map['decoration'],
          exampleBinding: map['exampleBinding'],
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
      'bindableSources': bindableSources,
      'decoration': decoration,
      'exampleBinding': exampleBinding,
      'fieldKey': fieldKey,
      'objectSchema': objectSchema,

      ...args,
    });
  }
}

class OrderListEditorSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/order_list_editor.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_OrderListEditor',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'bindableSources': SchemaHelper.anySchema,
      'decoration': SchemaHelper.anySchema,
      'exampleBinding': SchemaHelper.stringSchema,
      'fieldKey': SchemaHelper.stringSchema,
      'objectSchema': SchemaHelper.anySchema,
    },
  };
}
