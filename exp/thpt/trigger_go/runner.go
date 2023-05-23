package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"github.com/go-resty/resty/v2"
	"os"
	"strconv"
	"time"
)

func curTickMs() int64 {
	return time.Now().UnixNano() / int64(time.Millisecond)
}

type RequestThread struct {
	threadID                int
	duration                int
	baseURL                 string
	headers                 map[string]string
	latencies               []int64
	offsets                 []int64
	perThreadMaxConcurrency int
}

func (rt *RequestThread) Run(reqNums *[]int) {
	start := time.Now()
	startTick := curTickMs()
	var sleepTime time.Duration
	if rt.perThreadMaxConcurrency >= 0 {
		sleepTime = time.Duration(time.Second.Nanoseconds()/int64(rt.perThreadMaxConcurrency)) * time.Nanosecond
	}
	for time.Since(start) < time.Duration(rt.duration)*time.Second {
		if sleepTime > 0 {
			time.Sleep(sleepTime)
		}
		tick := curTickMs()
		_, err := resty.New().R().
			SetHeaders(rt.headers).
			SetBody("{}").
			Post(rt.baseURL)
		if err != nil {
			continue
		}
		fiTick := curTickMs()
		latency := fiTick - tick
		offset := fiTick - startTick
		rt.latencies = append(rt.latencies, latency)
		rt.offsets = append(rt.offsets, offset)
		(*reqNums)[rt.threadID]++
	}
}

type ThroughputThread struct {
	intervalMs int
	thptList   [][]string
	seq        int
	running    bool
}

func (tt *ThroughputThread) Run(reqNums *[]int) {
	sleepMS := time.Duration(tt.intervalMs) * time.Millisecond
	for tt.running {
		tick := curTickMs()
		time.Sleep(sleepMS)
		passedSec := float64(curTickMs()-tick) / 1000
		totalRequests := 0
		for i, n := range *reqNums {
			totalRequests += n
			(*reqNums)[i] = 0
		}
		tt.thptList = append(tt.thptList, []string{strconv.Itoa(tt.seq), fmt.Sprintf("%.2f", float64(totalRequests)/passedSec)})
		tt.seq++
	}
}

func main() {
	var egressThpt, threadNum, runTime, intervalMs int
	var outDir string

	flag.IntVar(&egressThpt, "concurrency", -1, "Client egress concurrency upperbound. If not set, then no limit")
	flag.IntVar(&threadNum, "threads", 2, "Concurrent thread number")
	flag.IntVar(&runTime, "run_time", 10, "Running seconds")
	flag.IntVar(&intervalMs, "interval_ms", 100, "Interval in millisecond")
	flag.StringVar(&outDir, "out_dir", "out", "Output directory")

	flag.Parse()

	fmt.Printf("Output to dir %s\n", outDir)

	if _, err := os.Stat(outDir); os.IsNotExist(err) {
		os.Mkdir(outDir, os.ModePerm)
	}
	perThreadMaxConcurrency := -1
	if egressThpt < 0 {
		perThreadMaxConcurrency = -1
	} else if egressThpt <= threadNum {
		perThreadMaxConcurrency = 1
	} else {
		perThreadMaxConcurrency = egressThpt / threadNum
	}
	fmt.Printf("Per Thread concurrency %v\n", perThreadMaxConcurrency)
	duration := runTime
	baseURL := "http://splitter-00001-private"
	headers := map[string]string{
		"Ce-Id":          "536808d3-88be-4077-9d7a-a3f162705f79",
		"Ce-Specversion": "1.0",
		"Ce-Type":        "dev.knative.sources.ping",
		"Ce-Source":      "ping-pong",
		"Content-Type":   "application/json",
	}
	latencyFile := outDir + "/latency.csv"
	thptFile := outDir + "/thpt.csv"
	thptIntervalMs := intervalMs

	threadsList := make([]*RequestThread, threadNum)
	reqNums := make([]int, threadNum)
	for i := range threadsList {
		threadsList[i] = &RequestThread{
			threadID:                i,
			duration:                duration,
			baseURL:                 baseURL,
			headers:                 headers,
			perThreadMaxConcurrency: perThreadMaxConcurrency,
		}
	}

	tt := &ThroughputThread{
		intervalMs: thptIntervalMs,
		thptList:   make([][]string, 0),
		seq:        0,
		running:    true,
	}
	go tt.Run(&reqNums)

	for i := 0; i < threadNum; i++ {
		go threadsList[i].Run(&reqNums)
		//time.Sleep(time.Duration(duration/threadNum) * time.Second)
	}

	time.Sleep(time.Duration(duration+1) * time.Second)
	tt.running = false

	latencies := make([][]string, 0)
	for i := 0; i < threadNum; i++ {
		latencies = append(latencies, threadsList[i].combineLatencies()...)
	}

	WriteFile(latencyFile, latencies, []string{"Offset", "Latency"})
	WriteFile(thptFile, tt.thptList, []string{"Seq", "Throughput"})

	fmt.Println("\nFinished.")
}

func (rt *RequestThread) combineLatencies() [][]string {
	latencies := make([][]string, 0)
	for i := 0; i < len(rt.offsets); i++ {
		latencies = append(latencies, []string{strconv.FormatInt(rt.offsets[i], 10), strconv.FormatInt(rt.latencies[i], 10)})
	}
	return latencies
}

func WriteFile(file string, data [][]string, header []string) {
	f, err := os.Create(file)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	if err := w.Write(header); err != nil {
		panic(err)
	}

	for _, record := range data {
		if err := w.Write(record); err != nil {
			panic(err)
		}
	}

	w.Flush()

	if err := w.Error(); err != nil {
		panic(err)
	}
}
