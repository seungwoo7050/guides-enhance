package dev.guides.spring.kafkaavro;

public record TaskSubmitted(String taskId, long itemCount, String category) {}
