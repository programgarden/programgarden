// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'plugin_select_builder.dart';

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

class PluginSelectBuilder extends _PluginSelectBuilder {
  const PluginSelectBuilder({required super.args});

  static const kType = 'plugin_select';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static PluginSelectBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => PluginSelectBuilder(args: map);

  @override
  PluginSelectBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = PluginSelectBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _PluginSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _PluginSelect(
      decoration: model.decoration,
      key: key,
      pluginCategory: model.pluginCategory,
    );
  }
}

class JsonPluginSelect extends JsonWidgetData {
  JsonPluginSelect({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.decoration,
    this.pluginCategory,
  }) : super(
         jsonWidgetArgs: PluginSelectBuilderModel.fromDynamic(
           {
             'decoration': decoration,
             'pluginCategory': pluginCategory,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => PluginSelectBuilder(
           args: PluginSelectBuilderModel.fromDynamic(
             {
               'decoration': decoration,
               'pluginCategory': pluginCategory,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: PluginSelectBuilder.kType,
       );

  final dynamic decoration;

  final String? pluginCategory;
}

class PluginSelectBuilderModel extends JsonWidgetBuilderModel {
  const PluginSelectBuilderModel(
    super.args, {
    this.decoration,
    this.pluginCategory,
  });

  final dynamic decoration;

  final String? pluginCategory;

  static PluginSelectBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[PluginSelectBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static PluginSelectBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    PluginSelectBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is PluginSelectBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = PluginSelectBuilderModel(
          args,
          decoration: map['decoration'],
          pluginCategory: map['pluginCategory'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'decoration': decoration,
      'pluginCategory': pluginCategory,

      ...args,
    });
  }
}

class PluginSelectSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/plugin_select.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_PluginSelect',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'decoration': SchemaHelper.anySchema,
      'pluginCategory': SchemaHelper.stringSchema,
    },
  };
}
