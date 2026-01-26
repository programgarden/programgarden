import 'package:flutter/material.dart';
import 'package:json_dynamic_widget/json_dynamic_widget.dart';
import 'package:intl/intl.dart';

part 'date_picker_builder.g.dart';

/// 날짜 선택 빌더
///
/// Fixed 모드에서 날짜를 캘린더로 선택할 수 있게 합니다.
///
/// JSON 구조:
/// ```json
/// {
///   "type": "custom_date_picker",
///   "args": {
///     "fieldKey": "start_date",
///     "decoration": {
///       "labelText": "시작일"
///     },
///     "initialValue": "2024-01-01",
///     "firstDate": "2020-01-01",
///     "lastDate": "2030-12-31",
///     "dateFormat": "yyyy-MM-dd"
///   }
/// }
/// ```
@jsonWidget
abstract class _DatePickerBuilder extends JsonWidgetBuilder {
  const _DatePickerBuilder({required super.args});

  @override
  _DatePicker buildCustom({
    ChildWidgetBuilder? childBuilder,
    required BuildContext context,
    required JsonWidgetData data,
    Key? key,
  });
}

class _DatePicker extends StatefulWidget {
  const _DatePicker({
    required this.fieldKey,
    this.decoration,
    this.initialValue,
    this.firstDate,
    this.lastDate,
    this.dateFormat,
    @JsonBuildArg() required this.data,
    super.key,
  });

  final String fieldKey;
  final dynamic decoration;
  final String? initialValue;
  final String? firstDate;
  final String? lastDate;
  final String? dateFormat;
  final JsonWidgetData data;

  @override
  State<_DatePicker> createState() => _DatePickerState();
}

class _DatePickerState extends State<_DatePicker> {
  late TextEditingController _controller;
  late DateFormat _formatter;
  DateTime? _selectedDate;

  @override
  void initState() {
    super.initState();
    _formatter = DateFormat(widget.dateFormat ?? 'yyyy-MM-dd');

    // 초기값 파싱
    _selectedDate = _parseDate(widget.initialValue);
    _controller = TextEditingController(
      text: _selectedDate != null ? _formatter.format(_selectedDate!) : '',
    );

    // 초기값을 레지스트리에 저장
    if (_selectedDate != null) {
      widget.data.jsonWidgetRegistry.setValue(
        widget.fieldKey,
        _formatter.format(_selectedDate!),
      );
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  DateTime? _parseDate(String? dateStr) {
    if (dateStr == null || dateStr.isEmpty) return null;

    // {{ }} 표현식인 경우 오늘 날짜 사용
    if (dateStr.contains('{{') && dateStr.contains('}}')) {
      return DateTime.now();
    }

    try {
      return DateTime.parse(dateStr);
    } catch (e) {
      debugPrint('[DatePicker] Failed to parse date: $dateStr');
      return null;
    }
  }

  DateTime _getFirstDate() {
    return _parseDate(widget.firstDate) ?? DateTime(2020, 1, 1);
  }

  DateTime _getLastDate() {
    return _parseDate(widget.lastDate) ?? DateTime(2030, 12, 31);
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate ?? DateTime.now(),
      firstDate: _getFirstDate(),
      lastDate: _getLastDate(),
      locale: const Locale('ko', 'KR'),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: Theme.of(context).colorScheme,
          ),
          child: child!,
        );
      },
    );

    if (picked != null && picked != _selectedDate) {
      setState(() {
        _selectedDate = picked;
        _controller.text = _formatter.format(picked);
      });

      // 레지스트리에 값 저장
      widget.data.jsonWidgetRegistry.setValue(
        widget.fieldKey,
        _formatter.format(picked),
      );
    }
  }

  InputDecoration _buildDecoration() {
    final dec = widget.decoration;
    String? labelText;
    String? hintText;

    if (dec is Map) {
      labelText = dec['labelText'] as String?;
      hintText = dec['hintText'] as String?;
    }

    return InputDecoration(
      labelText: labelText,
      hintText: hintText ?? 'YYYY-MM-DD',
      border: const OutlineInputBorder(),
      suffixIcon: IconButton(
        icon: const Icon(Icons.calendar_today),
        onPressed: _selectDate,
        tooltip: '날짜 선택',
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: _controller,
      decoration: _buildDecoration(),
      readOnly: true,
      onTap: _selectDate,
    );
  }
}
