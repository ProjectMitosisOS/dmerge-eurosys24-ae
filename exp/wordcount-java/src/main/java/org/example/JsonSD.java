package org.example;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;

public class JsonSD {
    public static byte[] serialize(Object obj) throws JsonProcessingException {
        ObjectMapper mapper = new ObjectMapper();
        return mapper.writeValueAsBytes(obj);
    }


    public static <T> T deserialize(byte[] bytes, Class<T> objClass) throws IOException {
        ObjectMapper mapper = new ObjectMapper();
        return mapper.readValue(bytes, objClass);
    }
}
