import split
import extract

if __name__ == '__main__':
    # Step1: Split
    result = split.lambda_handler(src_video=3, partition_num=3)
    events = result["detail"]["indeces"]
    return_list = []

    # Step2: Extract
    for event in events:  # Should run in parallel
        extract_result = extract.lambda_handler(event)
        return_list.append(extract_result)

    print(len(return_list))

    # Step3: Classify

