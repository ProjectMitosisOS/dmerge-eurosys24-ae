package org.example;

import com.esotericsoftware.kryo.Kryo;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class WordCountMapperReducer {

    private static List<String> splitter(String articlePath, int k) {
        List<String> lines = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(articlePath))) {
            String line;
            while ((line = br.readLine()) != null) {
                lines.add(line);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        List<String> outputLines = new ArrayList<>();
        int totalLines = lines.size();
        int linesPerFile = (int) Math.ceil((double) totalLines / k);

        for (int i = 0; i < k; i++) {
            int start = i * linesPerFile;
            int end = Math.min((i + 1) * linesPerFile, totalLines);
            List<String> sublist = lines.subList(start, end);
            StringBuilder sb = new StringBuilder();
            for (String s : sublist) {
                sb.append(s).append("\n");
            }
            outputLines.add(sb.toString());
        }

        return outputLines;
    }

    private static Map<String, Integer> mapper(List<String> lines) {
        Map<String, Integer> wordCount = new HashMap<>();
        Pattern pattern = Pattern.compile("\\w+");

        for (String line : lines) {
            Matcher matcher = pattern.matcher(line.toLowerCase());
            while (matcher.find()) {
                String word = matcher.group();
                wordCount.put(word, wordCount.getOrDefault(word, 0) + 1);
            }
        }

        return wordCount;
    }

    private static Map<String, Integer> reducer(List<Map<String, Integer>> wordCounts) {
        Map<String, Integer> wordCount = new HashMap<>();

        for (Map<String, Integer> wc : wordCounts) {
            for (Map.Entry<String, Integer> entry : wc.entrySet()) {
                String word = entry.getKey();
                int count = entry.getValue();
                wordCount.put(word, wordCount.getOrDefault(word, 0) + count);
            }
        }

        return wordCount;
    }

    public static void main(String[] args) throws IOException {
        final String articlePath = "../wordcount/datasets/OliverTwist_CharlesDickens/OliverTwist_CharlesDickens_French.txt";
        final int k = 8;
        long executeTime = 0, sdTime = 0, sdByteSize = 0;
        Instant start, end;

        start = Instant.now();
        List<String> lines = splitter(articlePath, k);
        end = Instant.now();
        executeTime += Duration.between(start, end).toMillis();
        byte[] bytes;
        {
            start = Instant.now();
            bytes = KryoSD.serialize(lines);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
            sdByteSize += bytes.length;

            start = Instant.now();
            lines = (List<String>) KryoSD.deserialize(bytes);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
        }

        start = Instant.now();
        List<Map<String, Integer>> wordCounts = new ArrayList<>();
        for (String line : lines) {
            wordCounts.add(mapper(Arrays.asList(line.split("\n"))));
        }
        end = Instant.now();
        executeTime += Duration.between(start, end).toMillis() / lines.size();

        {
            start = Instant.now();
            bytes = KryoSD.serialize(wordCounts);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
            sdByteSize += bytes.length;

            start = Instant.now();
            wordCounts = (List<Map<String, Integer>>) KryoSD.deserialize(bytes);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
        }

        start = Instant.now();
        Map<String, Integer> wordCount = reducer(wordCounts);
        end = Instant.now();
        executeTime += Duration.between(start, end).toMillis();

        {
            start = Instant.now();
            bytes = KryoSD.serialize(wordCount);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
            sdByteSize += bytes.length;

            start = Instant.now();
            wordCount = (Map<String, Integer>) KryoSD.deserialize(bytes);
            end = Instant.now();
            sdTime += Duration.between(start, end).toMillis();
        }

        System.out.printf("execute time: %d, sd time: %d, obj bytes len: %d",
                executeTime, sdTime, sdByteSize);
    }
}