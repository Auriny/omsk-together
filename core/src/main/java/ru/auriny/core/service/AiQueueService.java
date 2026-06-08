package ru.auriny.core.service;

import jakarta.annotation.Nullable;
import lombok.NonNull;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;

@Slf4j
@Service
@RequiredArgsConstructor
public class AiQueueService {
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    public void pushTask(@NonNull String queueName, @NonNull Object taskDto) {
        try {
            var json = objectMapper.writeValueAsString(taskDto);
            redisTemplate.opsForList().leftPush(queueName, json);
            log.debug("Отправлен батч в очередь {}: {}", queueName, json);
        } catch (Exception e) {
            log.error("Ошибка сериализации для очереди {}", queueName, e);
        }
    }

    @Nullable
    public <T> T waitForResult(String queueName, Class<T> responseType, long timeoutSeconds) {
        log.info("Ожидание ответа из очереди {} (таймаут {} сек)...", queueName, timeoutSeconds);
        var json = redisTemplate.opsForList().rightPop(queueName, Duration.ofSeconds(timeoutSeconds));

        if (json == null) {
            log.warn("Таймаут ожидания ответа из очереди {}", queueName);
            return null;
        }

        try {
            return objectMapper.readValue(json, responseType);
        } catch (Exception e) {
            log.error("Ошибка десериализации ответа из очереди {}", queueName, e);
            return null;
        }
    }
}