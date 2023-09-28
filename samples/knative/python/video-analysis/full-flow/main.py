import split
import extract
import classify

if __name__ == '__main__':
    # Step1: Split
    result = split.lambda_handler(src_video=1, partition_num=3)
    events = result["detail"]["indeces"]

    res_list = []
    # Step2: Extract
    for event in events:  # Should run in parallel
        extract_result = extract.lambda_handler(event)
        print(extract_result)
        # Step3: Classify
        classify_res = classify.handler(extract_result)
        print(classify_res)