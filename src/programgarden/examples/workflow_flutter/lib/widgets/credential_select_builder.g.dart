// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'credential_select_builder.dart';

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

class CredentialSelectBuilder extends _CredentialSelectBuilder {
  const CredentialSelectBuilder({required super.args});

  static const kType = 'credential_select';

  /// Constant that can be referenced for the builder's type.
  @override
  String get type => kType;

  /// Static function that is capable of decoding the widget from a dynamic JSON
  /// or YAML set of values.
  static CredentialSelectBuilder fromDynamic(
    dynamic map, {
    JsonWidgetRegistry? registry,
  }) => CredentialSelectBuilder(args: map);

  @override
  CredentialSelectBuilderModel createModel({
    ChildWidgetBuilder? childBuilder,
    required JsonWidgetData data,
  }) {
    final model = CredentialSelectBuilderModel.fromDynamic(
      args,
      registry: data.jsonWidgetRegistry,
    );

    return model;
  }

  @override
  _CredentialSelect buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  }) {
    final model = createModel(childBuilder: childBuilder, data: data);

    return _CredentialSelect(
      credentialTypes: model.credentialTypes,
      decoration: model.decoration,
      key: key,
      onAdd: model.onAdd,
      onEdit: model.onEdit,
    );
  }
}

class JsonCredentialSelect extends JsonWidgetData {
  JsonCredentialSelect({
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
    this.credentialTypes,
    this.decoration,
    this.onAdd,
    this.onEdit,
  }) : super(
         jsonWidgetArgs: CredentialSelectBuilderModel.fromDynamic(
           {
             'credentialTypes': credentialTypes,
             'decoration': decoration,
             'onAdd': onAdd,
             'onEdit': onEdit,

             ...args,
           },
           args: args,
           registry: registry,
         ),
         jsonWidgetBuilder: () => CredentialSelectBuilder(
           args: CredentialSelectBuilderModel.fromDynamic(
             {
               'credentialTypes': credentialTypes,
               'decoration': decoration,
               'onAdd': onAdd,
               'onEdit': onEdit,

               ...args,
             },
             args: args,
             registry: registry,
           ),
         ),
         jsonWidgetType: CredentialSelectBuilder.kType,
       );

  final List<dynamic>? credentialTypes;

  final dynamic decoration;

  final void Function()? onAdd;

  final void Function(String)? onEdit;
}

class CredentialSelectBuilderModel extends JsonWidgetBuilderModel {
  const CredentialSelectBuilderModel(
    super.args, {
    this.credentialTypes,
    this.decoration,
    this.onAdd,
    this.onEdit,
  });

  final List<dynamic>? credentialTypes;

  final dynamic decoration;

  final void Function()? onAdd;

  final void Function(String)? onEdit;

  static CredentialSelectBuilderModel fromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    final result = maybeFromDynamic(map, args: args, registry: registry);

    if (result == null) {
      throw Exception(
        '[CredentialSelectBuilder]: requested to parse from dynamic, but the input is null.',
      );
    }

    return result;
  }

  static CredentialSelectBuilderModel? maybeFromDynamic(
    dynamic map, {
    Map<String, dynamic> args = const {},
    JsonWidgetRegistry? registry,
  }) {
    CredentialSelectBuilderModel? result;

    if (map != null) {
      if (map is String) {
        map = yaon.parse(map, normalize: true);
      }

      if (map is CredentialSelectBuilderModel) {
        result = map;
      } else {
        registry ??= JsonWidgetRegistry.instance;
        map = registry.processArgs(map, <String>{}).value;
        result = CredentialSelectBuilderModel(
          args,
          credentialTypes: map['credentialTypes'],
          decoration: map['decoration'],
          onAdd: map['onAdd'],
          onEdit: map['onEdit'],
        );
      }
    }

    return result;
  }

  @override
  Map<String, dynamic> toJson() {
    return JsonClass.removeNull({
      'credentialTypes': credentialTypes,
      'decoration': decoration,
      'onAdd': onAdd,
      'onEdit': onEdit,

      ...args,
    });
  }
}

class CredentialSelectSchema {
  static const id =
      'https://peiffer-innovations.github.io/flutter_json_schemas/schemas/workflow_flutter/credential_select.json';

  static final schema = <String, Object>{
    r'$schema': 'http://json-schema.org/draft-07/schema#',
    r'$id': id,
    'title': '_CredentialSelect',
    'type': 'object',
    'additionalProperties': false,
    'properties': {
      'credentialTypes': SchemaHelper.anySchema,
      'decoration': SchemaHelper.anySchema,
      'onAdd': SchemaHelper.anySchema,
      'onEdit': SchemaHelper.anySchema,
    },
  };
}
