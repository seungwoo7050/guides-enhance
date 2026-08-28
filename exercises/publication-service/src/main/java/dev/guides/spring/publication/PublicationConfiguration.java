package dev.guides.spring.publication;

import java.net.http.HttpClient;
import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration(proxyBeanMethods = false)
public class PublicationConfiguration {
  @Bean
  Clock clock() {
    return Clock.systemUTC();
  }

  @Bean
  RestClient policyRestClient(
      RestClient.Builder builder,
      PolicyClientProperties properties) {
    HttpClient httpClient = HttpClient.newBuilder()
        .connectTimeout(properties.timeout())
        .version(HttpClient.Version.HTTP_1_1)
        .build();
    JdkClientHttpRequestFactory requestFactory =
        new JdkClientHttpRequestFactory(httpClient);
    requestFactory.setReadTimeout(properties.timeout());
    return builder
        .baseUrl(properties.baseUrl().toString())
        .requestFactory(requestFactory)
        .build();
  }
}
