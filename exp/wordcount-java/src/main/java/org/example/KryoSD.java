package org.example;

import com.esotericsoftware.kryo.Kryo;
import com.esotericsoftware.kryo.io.ByteBufferInput;
import com.esotericsoftware.kryo.io.ByteBufferOutput;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.*;

// https://www.alibabacloud.com/blog/an-introduction-and-comparison-of-several-common-java-serialization-frameworks_597900
// ZCOT
// Kryo is the Default SD tool used in Spark
public class KryoSD {
    private static final ThreadLocal<Kryo> kryoThreadLocal = ThreadLocal.withInitial(() -> {
        Kryo kryo = new Kryo();
        kryo.setRegistrationRequired(false);
        return kryo;
    });

    public static byte[] serialize(Object object) {
        Kryo kryo = kryoThreadLocal.get();
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        ByteBufferOutput output = new ByteBufferOutput(baos);
        kryo.writeClassAndObject(output, object);
        output.flush();
        return baos.toByteArray();
    }

    public static Object deserialize(byte[] bytes) {
        Kryo kryo = kryoThreadLocal.get();
        ByteArrayInputStream bais = new ByteArrayInputStream(bytes);
        ByteBufferInput input = new ByteBufferInput(bais);
        return kryo.readClassAndObject(input);
    }
}
