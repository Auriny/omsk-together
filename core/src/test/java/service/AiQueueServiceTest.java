package service;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.data.redis.core.ListOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import ru.auriny.core.service.AiQueueService;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

public class AiQueueServiceTest {

    @Test
    void pushTaskHandlesSerializationError() throws Exception {
        var redisTemplate = Mockito.mock(StringRedisTemplate.class);
        @SuppressWarnings("unchecked")
        var listOps = (ListOperations<String, String>) Mockito.mock(ListOperations.class);
        when(redisTemplate.opsForList()).thenReturn(listOps);

        var badObjectMapper = Mockito.mock(ObjectMapper.class);
        when(badObjectMapper.writeValueAsString(any()))
                .thenThrow(Mockito.mock(JacksonException.class));

        AiQueueService aiQueueService = new AiQueueService(redisTemplate, badObjectMapper);

        assertDoesNotThrow(() -> aiQueueService.pushTask("test-queue", new Object()));
        verify(listOps, never()).leftPush(anyString(), anyString());
    }

    @Test
    void waitForResultReturnsNullOnDeserializationError() {
        var redisTemplate = Mockito.mock(StringRedisTemplate.class);
        @SuppressWarnings("unchecked")
        var listOps = (ListOperations<String, String>) Mockito.mock(ListOperations.class);
        when(redisTemplate.opsForList()).thenReturn(listOps);

        when(listOps.rightPop(eq("test-queue"), eq(Duration.ofSeconds(10))))
                .thenReturn("{invalid}");

        AiQueueService aiQueueService = new AiQueueService(redisTemplate, new ObjectMapper());

        Object result = aiQueueService.waitForResult("test-queue", Object.class, 10);

        assertNull(result);
    }

    @Test
    void waitForResultReturnsNullOnTimeout() {
        var redisTemplate = Mockito.mock(StringRedisTemplate.class);
        @SuppressWarnings("unchecked")
        var listOps = (ListOperations<String, String>) Mockito.mock(ListOperations.class);
        when(redisTemplate.opsForList()).thenReturn(listOps);

        when(listOps.rightPop(eq("test-queue"), eq(Duration.ofSeconds(10))))
                .thenReturn(null);

        AiQueueService aiQueueService = new AiQueueService(redisTemplate, new ObjectMapper());

        Object result = aiQueueService.waitForResult("test-queue", Object.class, 10);

        assertNull(result);
    }
}