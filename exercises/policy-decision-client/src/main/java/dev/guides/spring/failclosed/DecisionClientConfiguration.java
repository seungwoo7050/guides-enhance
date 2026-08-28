package dev.guides.spring.failclosed;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class DecisionClientConfiguration {
  // [Implementation 2] 연결·읽기 timeout을 실제 HTTP 요청에 적용
  // 설정값을 검증하는 데 그치지 않고 request factory에 전달합니다.
  @Bean
  RestClient decisionRestClient(RestClient.Builder builder, DecisionClientProperties properties) {
    var factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(properties.connectTimeout());
    factory.setReadTimeout(properties.readTimeout());
    return builder.baseUrl(properties.baseUrl()).requestFactory(factory).build();
  }
}
