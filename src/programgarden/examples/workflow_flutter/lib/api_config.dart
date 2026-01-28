import 'package:http/http.dart' as http;

/// API 서버 설정
///
/// 1차: dev.ancon-bicolor.ts.net:8766
/// 2차 (fallback): localhost:8766
class ApiConfig {
  static const _primaryHost = 'http://jyj-mac.ancon-bicolor.ts.net:8766';
  static const _fallbackHost = 'http://localhost:8766';

  static String _baseUrl = _primaryHost;
  static bool _resolved = false;

  /// 현재 사용 중인 base URL
  static String get baseUrl => _baseUrl;

  /// 서버 연결 확인 및 fallback 처리
  static Future<void> resolve() async {
    if (_resolved) return;

    try {
      final response = await http
          .get(Uri.parse('$_primaryHost/api/node-types?locale=ko'))
          .timeout(const Duration(seconds: 3));
      if (response.statusCode == 200) {
        _baseUrl = _primaryHost;
        _resolved = true;
        return;
      }
    } catch (_) {
      // primary 실패 → fallback
    }

    _baseUrl = _fallbackHost;
    _resolved = true;
  }

  /// URL 생성 헬퍼
  static Uri uri(String path, {Map<String, String>? queryParams}) {
    final url = '$_baseUrl$path';
    if (queryParams != null && queryParams.isNotEmpty) {
      return Uri.parse(url).replace(queryParameters: queryParams);
    }
    return Uri.parse(url);
  }

  /// 테스트용 리셋
  static void reset() {
    _baseUrl = _primaryHost;
    _resolved = false;
  }
}
